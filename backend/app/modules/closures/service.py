"""結案與倉儲商業邏輯：結單條件檢核、轉待取件、入庫/出庫、結案。

Reads B's ``Wip`` + D's ``WipExecution`` (fine-grained ``exec_status`` / abort),
D's ``reports`` and ``storage`` (D-owned, Chinese statuses kept), and writes A's
``OrderModel.status`` as English ``OrderStatus`` values — rendered back to
Chinese in responses for D's frontend. Applicant email is resolved from
``users`` by ``applicant_id``. See [[cd-yields-to-ab-models]].
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import OrderStatus, ReportStatus, StorageStatus, WipStatus
from app.common.enums.role_d_zh import ORDER_ZH, REPORT_ZH, STORAGE_ZH
from app.common.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import OrderModel, StorageHistory
from app.modules.closures.repository import ClosureRepository
from app.modules.closures.serializers import storage_dict

logger = logging.getLogger(__name__)

# WIP 已結束（fine-grained exec_status，英文；無 exec row 視為未結束）
ENDED_EXEC = {WipStatus.COMPLETED.value, WipStatus.TERMINATED.value}

# 中止申請待主管判定標記（存於 wip_execution.abort_status）
ABORT_PENDING = "待主管判定"

# B 的 samples 狀態：樣品已離開實驗階段、進入交付/倉儲/返還/取件（即可結案）。
# 不含 received/split/pending_transfer（仍在實驗前或交付佇列、尚未點交付）。
DELIVERED_SAMPLE_STATES = {
    "transferring",
    "outbound",
    "in_storage",
    "pending_return",
    "picked_up",
    "pending_receive",
}

# A 的 orders.status 存英文 enum 值；回給 D 前端時轉回中文顯示。
_ORDER_EN_TO_ZH = {status.value: zh for status, zh in ORDER_ZH.items()}


def _now() -> datetime:
    return datetime.now()


def _order_zh(status: str) -> str:
    return _ORDER_EN_TO_ZH.get(status, status)


class ClosureService:
    def __init__(self, repo: ClosureRepository, scope: LabScope) -> None:
        self._repo = repo
        self._scope = scope

    async def _require_order(self, order_no: str) -> OrderModel:
        order = await self._repo.get_order(order_no)
        if order is None:
            raise NotFoundError(f"找不到委託單：{order_no}")
        return order

    async def _enforce_order_access(self, order_no: str) -> None:
        """An order is visible to a lab if any of its WIPs belong to that lab."""
        if self._scope.sees_all_labs:
            return
        if self._scope.restricted_without_lab:
            raise ForbiddenError("無權存取其他實驗室的委託單")
        labs = await self._repo.order_labs(order_no)
        if self._scope.lab_name not in labs:
            raise ForbiddenError("無權存取其他實驗室的委託單")

    async def check_closure(self, order_no: str) -> dict:
        """結單條件檢查（result_manage.md，需全部滿足）。"""
        await self._enforce_order_access(order_no)
        order = await self._require_order(order_no)
        return await self._compute_closure(order)

    async def _compute_closure(self, order: OrderModel) -> dict:
        order_no = order.order_no
        wips = await self._repo.list_wips_for_order(order_no)
        execs = await self._repo.get_execs_map([w.wip_no for w in wips])

        report_count = await self._repo.count_reports_in_status(
            order_no, [REPORT_ZH[ReportStatus.PUBLISHED], REPORT_ZH[ReportStatus.RETURNED]]
        )
        has_report = report_count > 0

        # 「樣品已入庫或待返還」改讀 B 的 samples 狀態（D 的 storage 表沒有任何流程
        # 會寫入）。實驗完成後樣品進入交付，點交付後即已離開實驗階段 → 可結案。
        sample_states = await self._repo.sample_statuses(order_no)
        sample_ok = bool(sample_states) and all(s in DELIVERED_SAMPLE_STATES for s in sample_states)

        no_open_abort = all(
            (e := execs.get(w.wip_no)) is None or e.abort_status != ABORT_PENDING for w in wips
        )
        all_ended = bool(wips) and all(
            (e := execs.get(w.wip_no)) is not None and e.exec_status in ENDED_EXEC for w in wips
        )
        data_collected = all(
            bool(e.result_note)
            for w in wips
            if (e := execs.get(w.wip_no)) is not None and e.exec_status == WipStatus.COMPLETED.value
        )
        conditions = [
            {"name": "所有實驗明細完成或終止", "ok": all_ended},
            {"name": "所有 WIP 已結束", "ok": all_ended},
            {"name": "數據已收集", "ok": data_collected},
            {"name": "無未結異常", "ok": no_open_abort},
            {"name": "樣品已入庫或待返還", "ok": sample_ok},
            {"name": "報告已建立或已回傳", "ok": has_report},
        ]
        return {
            "orderId": order_no,
            "status": _order_zh(order.status),
            "canClose": all(c["ok"] for c in conditions),
            "conditions": conditions,
        }

    async def list_closures(self) -> list[dict]:
        if self._scope.restricted_without_lab:
            return []
        orders = await self._repo.list_orders(self._scope.list_lab_filter())
        return [await self._compute_closure(o) for o in orders]

    async def list_storage(self, status: str | None = None) -> list[dict]:
        if self._scope.restricted_without_lab:
            return []
        items = await self._repo.list_storage(status, self._scope.list_lab_filter())
        return [storage_dict(s) for s in items]

    async def to_pickup(self, order_no: str) -> dict:
        await self._enforce_order_access(order_no)
        order = await self._require_order(order_no)
        check = await self.check_closure(order_no)
        if not check["canClose"]:
            unmet = "、".join(c["name"] for c in check["conditions"] if not c["ok"])
            raise ConflictError(f"尚未滿足結單條件：{unmet}")
        if order.status not in (
            OrderStatus.COMPLETED.value,
            OrderStatus.WAITING_REPORT_RETURN.value,
        ):
            raise ConflictError(f"委託單為「{_order_zh(order.status)}」，無法轉待取件")
        order.status = OrderStatus.WAITING_PICKUP.value
        await self._repo.commit()
        # pickup-reminder email (async via Celery, broker-fallback safe).
        await self._send_pickup_reminder(order)
        return {"orderId": order_no, "status": _order_zh(order.status)}

    async def storage_inbound(self, order_no: str, operator: str | None, note: str | None) -> dict:
        await self._enforce_order_access(order_no)
        items = await self._repo.storage_items(order_no)
        if not items:
            raise NotFoundError(f"委託單 {order_no} 無倉儲紀錄")
        for s in items:
            if s.status == STORAGE_ZH[StorageStatus.IN_LAB]:
                s.status = STORAGE_ZH[StorageStatus.STORED]
                s.history.append(
                    StorageHistory(
                        time=_now(), action="入庫", actor=operator or "系統", note=note or ""
                    )
                )
        await self._repo.commit()
        return {"orderId": order_no, "items": [storage_dict(s) for s in items]}

    async def storage_outbound(self, order_no: str, operator: str | None, note: str | None) -> dict:
        await self._enforce_order_access(order_no)
        order = await self._require_order(order_no)
        if order.status != OrderStatus.WAITING_PICKUP.value:
            raise ConflictError(f"委託單為「{_order_zh(order.status)}」，僅「待取件」可出庫取件")
        items = await self._repo.storage_items(order_no)
        if not items:
            raise NotFoundError(f"委託單 {order_no} 無倉儲紀錄")
        for s in items:
            s.status = STORAGE_ZH[StorageStatus.PICKED_UP]
            s.history.append(
                StorageHistory(
                    time=_now(), action="出庫取件", actor=operator or "系統", note=note or ""
                )
            )
        await self._repo.commit()
        return {"orderId": order_no, "items": [storage_dict(s) for s in items]}

    async def close_order(self, order_no: str, operator: str | None) -> dict:
        await self._enforce_order_access(order_no)
        order = await self._require_order(order_no)
        if order.status != OrderStatus.WAITING_PICKUP.value:
            raise ConflictError(f"委託單為「{_order_zh(order.status)}」，僅「待取件」可結案")
        items = await self._repo.storage_items(order_no)
        # An order at waiting_pickup with no storage rows means the inbound
        # step never ran (or all rows were purged) — treat as "not yet
        # picked up", not as a free pass. Previously ``if items and not
        # all(...)`` was falsy on empty items, letting an unpicked order
        # flip to CLOSED before the requester had actually picked up.
        if not items or not all(s.status == STORAGE_ZH[StorageStatus.PICKED_UP] for s in items):
            raise ConflictError("尚有樣品未取件，無法結案")
        order.status = OrderStatus.CLOSED.value
        await self._repo.commit()
        return {"orderId": order_no, "status": _order_zh(order.status)}

    async def _send_pickup_reminder(self, order: OrderModel) -> None:
        """Enqueue the pickup-reminder email; degrade gracefully if the broker is down.

        TODO(recipient): resolve a real address from ``users`` via ``applicant_id``;
        if that fails fall back to the raw ``applicant_id`` so the task is still wired.
        Replace once orders carry an ``applicant_email`` (or a FK to ``users``).
        """
        from app.workers.email_sender import send_pickup_reminder_email

        recipient = await self._repo.find_user_email_by_applicant(order.applicant_id)
        if not recipient:
            recipient = order.applicant_id
            logger.warning(
                "No email resolved for applicant %r on order %s; using placeholder %r",
                order.applicant_id,
                order.order_no,
                recipient,
            )

        try:
            send_pickup_reminder_email.delay(
                to=recipient, order_id=order.order_no, applicant=order.applicant_id
            )
        except Exception:  # broker unavailable → synchronous fallback
            logger.warning(
                "Celery broker unavailable; sending pickup reminder synchronously for order %s",
                order.order_no,
            )
            try:
                send_pickup_reminder_email.run(
                    to=recipient, order_id=order.order_no, applicant=order.applicant_id
                )
            except Exception:
                logger.exception("Failed to send pickup reminder for order %s", order.order_no)
