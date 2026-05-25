"""實驗執行商業邏輯：上下機、進度、結果、確認、中止、機台自動完成。

Ported from Role D's flat ``app/store/experiments.py`` + ``store/common.py``,
converted from sync to async. Status values use the canonical English enums
from ``app.common.enums``.

Status-value mapping (Role D Chinese → canonical English):
    WipStatus.PENDING_CHECKIN 待上機  → WAITING_LOAD
    WipStatus.RUNNING 執行中         → RUNNING
    WipStatus.CHECKED_OUT 已下機     → UNLOADED
    WipStatus.PENDING_CONFIRM 待確認 → WAITING_CONFIRM
    WipStatus.DONE 已完成            → COMPLETED
    WipStatus.TERMINATED 已終止      → TERMINATED
    OrderStatus.DISPATCHED 排程中    → SCHEDULED
    OrderStatus.RUNNING 實驗中       → IN_PROGRESS
    OrderStatus.PENDING_RESULT       → WAITING_RESULT_CONFIRM
    OrderStatus.DONE 已完成          → COMPLETED
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.common.enums import OrderStatus, WipStatus
from app.common.enums.role_d_zh import ORDER_ZH, WIP_ZH
from app.common.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import Wip, WipHistory
from app.modules.experiment_runs.repository import ExperimentRunRepository
from app.modules.experiment_runs.serializers import wip_dict

logger = logging.getLogger(__name__)

# WIP 已結束狀態
ENDED_WIP = {WIP_ZH[WipStatus.COMPLETED], WIP_ZH[WipStatus.TERMINATED]}

# 中止申請 pending 標記
ABORT_PENDING = "待主管判定"


def _now() -> datetime:
    return datetime.now()


def _event(wip: Wip, action: str, actor: str, note: str = "") -> None:
    """新增一筆 WIP 履歷。"""
    wip.history.append(WipHistory(time=_now(), action=action, actor=actor, note=note))


def _refresh_order_after_result(order) -> None:
    """所有 WIP 都到 待確認/已完成/已終止 時，委託單進入待結果確認。"""
    ended = {
        WIP_ZH[WipStatus.WAITING_CONFIRM],
        WIP_ZH[WipStatus.COMPLETED],
        WIP_ZH[WipStatus.TERMINATED],
    }
    if order.wips and all(w.status in ended for w in order.wips):
        if order.status == ORDER_ZH[OrderStatus.IN_PROGRESS]:
            order.status = ORDER_ZH[OrderStatus.WAITING_RESULT_CONFIRM]


def _refresh_order_after_confirm(order) -> None:
    """所有 WIP 已完成/已終止 時，委託單進入已完成。"""
    if order.wips and all(w.status in ENDED_WIP for w in order.wips):
        order.status = ORDER_ZH[OrderStatus.COMPLETED]


class ExperimentRunService:
    def __init__(self, repo: ExperimentRunRepository) -> None:
        self._repo = repo

    async def _require_wip(self, wip_id: str) -> Wip:
        wip = await self._repo.get_wip(wip_id)
        if wip is None:
            raise NotFoundError(f"找不到 WIP：{wip_id}")
        return wip

    async def list_wips(self, status: str | None = None) -> list[dict]:
        wips = await self._repo.list_wips(status)
        return [wip_dict(w) for w in wips]

    async def get_wip(self, wip_id: str) -> dict:
        wip = await self._require_wip(wip_id)
        return wip_dict(wip)

    async def check_in(self, wip_id: str, operator: str, machine_id: str, recipe: str) -> dict:
        wip = await self._require_wip(wip_id)
        if wip.status != WIP_ZH[WipStatus.WAITING_LOAD]:
            raise ConflictError(f"WIP 目前為「{wip.status}」，僅「待上機」可上機登記")
        wip.status = WIP_ZH[WipStatus.RUNNING]
        wip.operator = operator
        wip.machine_id = machine_id
        wip.recipe = recipe
        wip.check_in_at = _now()
        _event(wip, "上機", operator, f"機台 {machine_id} / {recipe}")
        if wip.order.status == ORDER_ZH[OrderStatus.SCHEDULED]:
            wip.order.status = ORDER_ZH[OrderStatus.IN_PROGRESS]
        await self._repo.commit()
        return wip_dict(wip)

    async def check_out(self, wip_id: str, operator: str, note: str | None) -> dict:
        wip = await self._require_wip(wip_id)
        if wip.status != WIP_ZH[WipStatus.RUNNING]:
            raise ConflictError(f"WIP 目前為「{wip.status}」，僅「執行中」可下機登記")
        wip.status = WIP_ZH[WipStatus.UNLOADED]
        wip.check_out_at = _now()
        _event(wip, "下機", operator, note or "")
        await self._repo.commit()
        return wip_dict(wip)

    async def update_progress(self, wip_id: str, progress: int) -> dict:
        wip = await self._require_wip(wip_id)
        if wip.status != WIP_ZH[WipStatus.RUNNING]:
            raise ConflictError(f"WIP 目前為「{wip.status}」，僅「執行中」可更新進度")
        wip.progress = progress
        _event(wip, "更新進度", wip.operator or "系統", f"{progress}%")
        await self._repo.commit()
        return wip_dict(wip)

    async def upload_result(
        self, wip_id: str, note: str, raw_data_url: str | None, data_verified: bool
    ) -> dict:
        wip = await self._require_wip(wip_id)
        if wip.status not in (WIP_ZH[WipStatus.RUNNING], WIP_ZH[WipStatus.UNLOADED]):
            raise ConflictError(f"WIP 目前為「{wip.status}」，需在執行中或已下機才能上傳結果")
        if wip.status == WIP_ZH[WipStatus.RUNNING]:
            wip.check_out_at = _now()
            _event(wip, "下機", wip.operator or "系統", "上傳結果時自動下機")
        wip.status = WIP_ZH[WipStatus.WAITING_CONFIRM]
        wip.result_note = note
        wip.raw_data_url = raw_data_url
        wip.data_verified = data_verified
        wip.progress = 100
        _event(wip, "上傳結果", wip.operator or "系統", note)
        _refresh_order_after_result(wip.order)
        await self._repo.commit()
        return wip_dict(wip)

    async def confirm_result(self, wip_id: str, operator: str) -> dict:
        wip = await self._require_wip(wip_id)
        if wip.status != WIP_ZH[WipStatus.WAITING_CONFIRM]:
            raise ConflictError(f"WIP 目前為「{wip.status}」，僅「待確認」可確認結果")
        if not wip.data_verified:
            raise ValidationError("數據完整性尚未驗證，無法確認結果")
        wip.status = WIP_ZH[WipStatus.COMPLETED]
        _event(wip, "確認結果", operator, "")
        _refresh_order_after_confirm(wip.order)
        await self._repo.commit()
        return wip_dict(wip)

    async def request_abort(self, wip_id: str, reason: str, by: str) -> dict:
        wip = await self._require_wip(wip_id)
        if wip.status in ENDED_WIP:
            raise ConflictError(f"WIP 已是「{wip.status}」，不可再申請中止")
        if wip.abort_status == ABORT_PENDING:
            raise ConflictError("已有中止申請待主管判定")
        wip.abort_reason = reason
        wip.abort_by = by
        wip.abort_status = ABORT_PENDING
        wip.abort_requested_at = _now()
        _event(wip, "提出中止申請", by, reason)
        # 不改 order 狀態為 pending_chief，因為新 enum 沒有這個值
        # 保留原始邏輯的精神：標記有中止待審
        await self._repo.commit()
        return wip_dict(wip)

    async def review_abort(self, wip_id: str, approve: bool, note: str | None, by: str) -> dict:
        wip = await self._require_wip(wip_id)
        if wip.abort_status != ABORT_PENDING:
            raise ConflictError("此 WIP 無待審核的中止申請")
        if approve:
            wip.status = WIP_ZH[WipStatus.TERMINATED]
            wip.abort_status = "已終止"
            wip.abort_resolution = note or ""
            _event(wip, "主管核准終止", by, note or "")
            if all(w.status in ENDED_WIP for w in wip.order.wips):
                wip.order.status = ORDER_ZH[OrderStatus.COMPLETED]
        else:
            wip.status = WIP_ZH[WipStatus.RUNNING]
            wip.abort_status = "已駁回"
            wip.abort_resolution = note or ""
            _event(wip, "主管駁回中止，繼續實驗", by, note or "")
            wip.order.status = ORDER_ZH[OrderStatus.IN_PROGRESS]
        await self._repo.commit()
        return wip_dict(wip)

    async def apply_machine_completion(self, wip_id: str) -> bool:
        """機台自動回報完成（由 Celery 背景任務呼叫）。

        自動寫入數據並轉「待確認」（規則：機台回報完成不直接結案）。
        回傳是否有實際處理。
        """
        wip = await self._repo.get_wip(wip_id)
        if not wip or wip.status not in (WIP_ZH[WipStatus.RUNNING], WIP_ZH[WipStatus.UNLOADED]):
            return False
        if wip.status == WIP_ZH[WipStatus.RUNNING]:
            wip.check_out_at = _now()
            _event(wip, "下機", "系統(機台)", "機台回報完成自動下機")
        wip.status = WIP_ZH[WipStatus.WAITING_CONFIRM]
        wip.progress = 100
        wip.data_verified = False
        if not wip.result_note:
            wip.result_note = f"機台 {wip.machine_id} 自動回報完成，數據已寫入，待人員驗證"
        wip.raw_data_url = wip.raw_data_url or f"/data/{wip.wip_id}.auto.csv"
        _event(wip, "機台自動數據蒐集", "系統(機台)", "已寫入原始數據，進入待結果確認")
        _refresh_order_after_result(wip.order)
        await self._repo.commit()
        return True
