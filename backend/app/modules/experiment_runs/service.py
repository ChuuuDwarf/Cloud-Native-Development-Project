"""實驗執行商業邏輯：上下機、進度、結果、確認、中止、機台自動完成。

Operates on B's ``Wip`` (coarse English ``status``) plus D's ``WipExecution``
side row (fine-grained ``exec_status`` + machine/result/abort fields). Status
gates compare against ``exec_status`` (canonical English ``WipStatus``); B's
``wips.status`` only receives a coarse CHECK-valid value via ``WIP_EXEC_TO_B``.
Order status is written as A's English ``OrderStatus`` value. WIP history rows
use B's ``wip_histories`` columns (action / operator_name / description).

D's abort request lives in ``wip_execution`` (B's ``wips`` has no abort fields).
See [[cd-yields-to-ab-models]].
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import OrderStatus, WipStatus
from app.common.enums.role_d_zh import WIP_EXEC_TO_B
from app.common.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models import Wip, WipExecution, WipHistory
from app.db.models.labs import Lab
from app.modules.dashboard.publisher import publish_dashboard_event
from app.modules.experiment_runs.repository import ExperimentRunRepository
from app.modules.experiment_runs.serializers import wip_dict
from app.modules.reports.fake_data import generate_for_items

logger = logging.getLogger(__name__)

# WIP 已結束（fine-grained exec_status，英文）
ENDED_EXEC = {WipStatus.COMPLETED.value, WipStatus.TERMINATED.value}
# 進入「待結果確認」的判定集合
RESULT_READY_EXEC = {
    WipStatus.WAITING_CONFIRM.value,
    WipStatus.COMPLETED.value,
    WipStatus.TERMINATED.value,
}

# 中止申請 pending 標記
ABORT_PENDING = "待主管判定"

# 進度自動推進：Celery beat 每 2s 觸發一次（見 celery_app.py）。固定 2s 間隔
# 搭配每 tick +10%，0→100% 約 20 秒完成，確保展示時 30 秒內跑完。
PROGRESS_TICK_SECONDS = 2
PROGRESS_STEP_PERCENT = 10


def _next_progress_at() -> datetime:
    return _now() + timedelta(seconds=PROGRESS_TICK_SECONDS)


# B 的粗粒度 wips.status：WIP 必須已被派工（待上機）才能進入 D 的實驗執行。
# 對應 WIP_EXEC_TO_B[WAITING_LOAD]；由 C 的派工 assign 推進到此。
B_DISPATCHED = "dispatched"


def _now() -> datetime:
    return datetime.now()


def _set_status(wip: Wip, exec_row: WipExecution, status: WipStatus) -> None:
    """Set D's fine-grained exec_status and sync B's coarse wips.status."""
    exec_row.exec_status = status.value
    wip.status = WIP_EXEC_TO_B[status]


def _ensure_experiment_data(wip: Wip, exec_row: WipExecution) -> None:
    """機台收集的量測數據只產生並保存一次（供驗證時顯示、報告建立時沿用）。"""
    if not exec_row.experiment_data:
        items = [wip.experiment_item] if wip.experiment_item else []
        exec_row.experiment_data = generate_for_items(items)


def _event(wip: Wip, action: str, actor: str, note: str = "") -> None:
    """新增一筆 WIP 履歷（B 的 wip_histories）。"""
    wip.history.append(WipHistory(action=action, operator_name=actor, description=note))


class ExperimentRunService:
    def __init__(self, repo: ExperimentRunRepository, scope: LabScope) -> None:
        self._repo = repo
        self._scope = scope

    async def _require_wip(self, wip_no: str) -> Wip:
        """Load a WIP and enforce lab scoping (covers get + every operation)."""
        wip = await self._repo.get_wip(wip_no)
        if wip is None:
            raise NotFoundError(f"找不到 WIP：{wip_no}")
        if not self._scope.can_access_lab(wip.lab_name):
            raise ForbiddenError("無權存取其他實驗室的 WIP")
        return wip

    async def _publish_wip_pipeline_change(self, wip: Wip, event_name: str) -> None:
        """Best-effort dashboard SSE fanout for a WIP pipeline transition.

        WIP rows store the display name (Chinese); SSE channels are keyed by
        ``Lab.code`` (ASCII) to match what the SSE handler subscribes off
        (``CurrentUser.lab_code``). Translate via the labs table; fall back
        to the global channel if the row has no lab_name or the translation
        misses. All errors swallowed — a publish hiccup must not fail the
        request that already committed.
        """
        try:
            lab_code: str | None = None
            if wip is not None and wip.lab_name:
                lab_code = await self._repo.session.scalar(
                    select(Lab.code).where(Lab.name == wip.lab_name)
                )
            await publish_dashboard_event(lab_code, event_name)
        except Exception:
            logger.exception(
                "publish %s failed for wip=%s",
                event_name,
                wip.wip_no if wip else None,
            )

    async def _all_wips_in(self, order_no: str, statuses: set[str]) -> bool:
        """Whether every WIP of the order has an exec row in ``statuses``."""
        wips = await self._repo.list_wips_for_order(order_no)
        execs = await self._repo.get_execs_map([w.wip_no for w in wips])
        return bool(wips) and all(
            (e := execs.get(w.wip_no)) is not None and e.exec_status in statuses for w in wips
        )

    async def _refresh_order_after_result(self, order_no: str) -> None:
        order = await self._repo.get_order(order_no)
        if order is None or order.status != OrderStatus.IN_PROGRESS.value:
            return
        if await self._all_wips_in(order_no, RESULT_READY_EXEC):
            order.status = OrderStatus.WAITING_RESULT_CONFIRM.value

    async def _refresh_order_after_confirm(self, order_no: str) -> None:
        order = await self._repo.get_order(order_no)
        if order is None:
            return
        if await self._all_wips_in(order_no, ENDED_EXEC):
            order.status = OrderStatus.COMPLETED.value

    async def list_wips(self, status: str | None = None) -> list[dict]:
        if self._scope.restricted_without_lab:
            return []
        wips = await self._repo.list_wips(self._scope.list_lab_filter())
        wip_nos = [w.wip_no for w in wips]
        execs = await self._repo.get_execs_map(wip_nos)
        plans = await self._repo.get_dispatch_assignments(wip_nos)
        out = [wip_dict(w, execs.get(w.wip_no), plans.get(w.wip_no)) for w in wips]
        if status:
            out = [d for d in out if d["status"] == status]
        return out

    async def get_wip(self, wip_no: str) -> dict:
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        planned = await self._repo.get_dispatch_assignment(wip_no)
        return wip_dict(wip, exec_row, planned)

    async def list_operators(self, wip_no: str) -> list[dict]:
        """The WIP's lab members (人員/主管) for the 上機 operator picker."""
        wip = await self._require_wip(wip_no)
        if not wip.lab_name:
            return []
        role_zh = {"lab_engineer": "實驗室人員", "lab_supervisor": "實驗室主管"}
        out: dict[str, dict] = {}
        for name, role in await self._repo.list_lab_operators(wip.lab_name):
            # If a user has both roles, prefer the supervisor label.
            if name not in out or role == "lab_supervisor":
                out[name] = {"name": name, "role": role_zh.get(role, role)}
        return list(out.values())

    async def check_in(self, wip_no: str, operator: str, machine_id: str, recipe: str) -> dict:
        wip = await self._require_wip(wip_no)
        if wip.status != B_DISPATCHED:
            raise ConflictError("WIP 尚未派工（待上機），請先完成排程與派工後再上機")
        exec_row = await self._repo.ensure_exec(wip_no)
        if exec_row.exec_status != WipStatus.WAITING_LOAD.value:
            raise ConflictError("WIP 非「待上機」狀態，無法上機登記")
        _set_status(wip, exec_row, WipStatus.RUNNING)
        exec_row.operator = operator
        exec_row.machine_id = machine_id
        exec_row.recipe = recipe
        exec_row.check_in_at = _now()
        # 排定第一次進度自動推進（背景任務每隔隨機 3/5/8 秒 +1%）。
        exec_row.next_progress_at = _next_progress_at()
        _event(wip, "上機", operator, f"機台 {machine_id} / {recipe}")
        order = await self._repo.get_order(wip.order_no)
        if order and order.status == OrderStatus.SCHEDULED.value:
            order.status = OrderStatus.IN_PROGRESS.value
        await self._repo.commit()
        await self._publish_wip_pipeline_change(wip, "wip_check_in")
        return wip_dict(wip, exec_row)

    async def check_out(self, wip_no: str, operator: str, note: str | None) -> dict:
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        if exec_row is None or exec_row.exec_status != WipStatus.RUNNING.value:
            raise ConflictError("WIP 非「執行中」狀態，無法下機登記")
        _set_status(wip, exec_row, WipStatus.UNLOADED)
        exec_row.check_out_at = _now()
        exec_row.next_progress_at = None  # 離開執行中，停止自動推進
        _event(wip, "下機", operator, note or "")
        await self._repo.commit()
        return wip_dict(wip, exec_row)

    async def update_progress(self, wip_no: str, progress: int) -> dict:
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        if exec_row is None or exec_row.exec_status != WipStatus.RUNNING.value:
            raise ConflictError("WIP 非「執行中」狀態，無法更新進度")
        wip.progress = progress
        _event(wip, "更新進度", exec_row.operator or "系統", f"{progress}%")
        await self._repo.commit()
        return wip_dict(wip, exec_row)

    async def upload_result(
        self, wip_no: str, note: str, raw_data_url: str | None, data_verified: bool
    ) -> dict:
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        if exec_row is None or exec_row.exec_status not in (
            WipStatus.RUNNING.value,
            WipStatus.UNLOADED.value,
        ):
            raise ConflictError("需在執行中或已下機才能上傳結果")
        if exec_row.exec_status == WipStatus.RUNNING.value:
            exec_row.check_out_at = _now()
            _event(wip, "下機", exec_row.operator or "系統", "上傳結果時自動下機")
        _set_status(wip, exec_row, WipStatus.WAITING_CONFIRM)
        exec_row.result_note = note
        exec_row.raw_data_url = raw_data_url
        exec_row.data_verified = data_verified
        _ensure_experiment_data(wip, exec_row)  # 保存量測數據供驗證顯示
        exec_row.next_progress_at = None  # 已進待確認，停止自動推進
        wip.progress = 100
        _event(wip, "上傳結果", exec_row.operator or "系統", note)
        await self._repo.commit()
        await self._refresh_order_after_result(wip.order_no)
        await self._repo.commit()
        return wip_dict(wip, exec_row)

    async def verify_data(self, wip_no: str, operator: str) -> dict:
        """人工驗證原始數據完整性（待確認狀態）。

        機台自動回報完成的 WIP 落在「待確認 / 未驗證」，沒走過人工上傳結果，
        故無 ``data_verified``。此處讓人員在「待確認」狀態驗證數據，通過後
        ``confirm_result`` 才放行。
        """
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        if exec_row is None or exec_row.exec_status != WipStatus.WAITING_CONFIRM.value:
            raise ConflictError("WIP 非「待確認」狀態，無法驗證數據")
        if exec_row.data_verified:
            raise ConflictError("數據已驗證，無需重複驗證")
        exec_row.data_verified = True
        _event(wip, "數據驗證", operator, "已人工驗證數據完整性")
        await self._repo.commit()
        return wip_dict(wip, exec_row)

    async def confirm_result(self, wip_no: str, operator: str) -> dict:
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        if exec_row is None or exec_row.exec_status != WipStatus.WAITING_CONFIRM.value:
            raise ConflictError("WIP 非「待確認」狀態，無法確認結果")
        if not exec_row.data_verified:
            raise ValidationError("數據完整性尚未驗證，無法確認結果")
        _set_status(wip, exec_row, WipStatus.COMPLETED)
        # Stamp wips.completed_at so KPI 完工 / dashboard 24h windows pick
        # the WIP up. Without this the row sits at status=completed with a
        # NULL completed_at and disappears from every "completed today"
        # bucket. ``Wip.completed_at`` is a naive TIMESTAMP (B's migration);
        # use the same naive ``_now()`` the rest of this module uses.
        wip.completed_at = _now()
        _event(wip, "確認結果", operator, "")
        await self._repo.commit()
        await self._refresh_order_after_confirm(wip.order_no)
        await self._repo.commit()
        await self._advance_sample_flow(wip, operator)
        await self._publish_wip_pipeline_change(wip, "wip_completed")
        return wip_dict(wip, exec_row)

    async def _advance_sample_flow(self, wip: Wip, operator: str) -> None:
        """After a D completion, run B's sample-flow advance for the sample.

        B owns the sample / transfer / pickup flow; a WIP turning ``completed``
        is what moves the sample forward. Mirroring B's native WIP-complete
        behaviour here means:

        - an intermediate completion advances the sample to ``pending_transfer``
          (so it surfaces under /transfer 可交接至下一個 Lab), and
        - completing the sample's last experiment moves it to ``split`` and
          writes the "可通知使用者取件" history (so it surfaces under
          /transfer 待通知使用者取件).

        Best-effort: the confirmation itself is already committed, so a hiccup
        in the cross-owner sample flow must not fail the request. See
        [[cd-yields-to-ab-models]].
        """
        if wip.sample_id is None:
            return
        try:
            from app.services import wip_service

            await wip_service.update_sample_to_pending_transfer_if_ready(
                db=self._repo.session,
                sample_id=str(wip.sample_id),
                current_lab=wip.lab_name,
                next_location=None,
                operator_name=operator,
            )
            await self._repo.commit()
        except Exception:
            logger.exception(
                "Sample-flow advance failed for WIP %s (sample %s); confirmation already committed",
                wip.wip_no,
                wip.sample_id,
            )

    async def request_abort(self, wip_no: str, reason: str, by: str) -> dict:
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.ensure_exec(wip_no)
        if exec_row.exec_status in ENDED_EXEC:
            raise ConflictError("WIP 已結束，不可再申請中止")
        if exec_row.abort_status == ABORT_PENDING:
            raise ConflictError("已有中止申請待主管判定")
        exec_row.abort_reason = reason
        exec_row.abort_by = by
        exec_row.abort_status = ABORT_PENDING
        exec_row.abort_requested_at = _now()
        _event(wip, "提出中止申請", by, reason)
        await self._repo.commit()
        return wip_dict(wip, exec_row)

    async def review_abort(self, wip_no: str, approve: bool, note: str | None, by: str) -> dict:
        wip = await self._require_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        if exec_row is None or exec_row.abort_status != ABORT_PENDING:
            raise ConflictError("此 WIP 無待審核的中止申請")
        if approve:
            _set_status(wip, exec_row, WipStatus.TERMINATED)
            # Mirror confirm_result: stamp wips.terminated_at when the coarse
            # status flips to terminated, so dashboard / KPI windows that
            # filter on terminated_at find the row. Naive TIMESTAMP — use
            # the same naive ``_now()`` everywhere else in this module uses.
            wip.terminated_at = _now()
            exec_row.abort_status = "已終止"
            exec_row.abort_resolution = note or ""
            exec_row.next_progress_at = None  # 已終止，停止推進
            _event(wip, "主管核准終止", by, note or "")
            await self._repo.commit()
            await self._refresh_order_after_confirm(wip.order_no)
        else:
            _set_status(wip, exec_row, WipStatus.RUNNING)
            exec_row.abort_status = "已駁回"
            exec_row.abort_resolution = note or ""
            exec_row.next_progress_at = _next_progress_at()  # 繼續實驗，恢復推進
            _event(wip, "主管駁回中止，繼續實驗", by, note or "")
            order = await self._repo.get_order(wip.order_no)
            if order:
                order.status = OrderStatus.IN_PROGRESS.value
        await self._repo.commit()
        if approve:
            # Only fire the SSE on actual termination — a rejected abort
            # leaves the WIP running and doesn't change the dashboard slice.
            await self._publish_wip_pipeline_change(wip, "wip_terminated")
        return wip_dict(wip, exec_row)

    async def apply_machine_completion(self, wip_no: str) -> bool:
        """機台自動回報完成（由 Celery 背景任務呼叫）。"""
        wip = await self._repo.get_wip(wip_no)
        exec_row = await self._repo.get_exec(wip_no)
        if (
            wip is None
            or exec_row is None
            or exec_row.exec_status not in (WipStatus.RUNNING.value, WipStatus.UNLOADED.value)
        ):
            return False
        if exec_row.exec_status == WipStatus.RUNNING.value:
            exec_row.check_out_at = _now()
            _event(wip, "下機", "系統(機台)", "機台回報完成自動下機")
        _set_status(wip, exec_row, WipStatus.WAITING_CONFIRM)
        wip.progress = 100
        exec_row.next_progress_at = None  # 已完成推進
        exec_row.data_verified = False
        if not exec_row.result_note:
            exec_row.result_note = (
                f"機台 {exec_row.machine_id} 自動回報完成，數據已寫入，待人員驗證"
            )
        exec_row.raw_data_url = exec_row.raw_data_url or f"/data/{wip.wip_no}.auto.csv"
        _ensure_experiment_data(wip, exec_row)  # 機台收集的量測數據，保存供驗證顯示
        _event(wip, "機台自動數據蒐集", "系統(機台)", "已寫入原始數據，進入待結果確認")
        await self._repo.commit()
        await self._refresh_order_after_result(wip.order_no)
        await self._repo.commit()
        return True
