"""結案與倉儲商業邏輯：結單條件檢核、轉待取件、入庫/出庫、結案。

Ported from Role D's flat ``app/store/closures.py`` (+ the ``common.py`` helpers
it relied on), converted from sync to async and rewired onto the project's
canonical enums (``app.common.enums``) and error types (``app.common.errors``).

Status-value mapping (Role D Chinese → canonical English):
    OrderStatus.DONE 已完成              → COMPLETED
    OrderStatus.PENDING_REPORT 待報告回傳 → WAITING_REPORT_RETURN
    OrderStatus.PENDING_PICKUP 待取件     → WAITING_PICKUP
    OrderStatus.CLOSED 已結案            → CLOSED
    WipStatus.DONE 已完成                → COMPLETED
    WipStatus.TERMINATED 已終止          → TERMINATED
    ReportStatus.PUBLISHED/RETURNED      → published / returned
    StorageStatus.* (in_lab/stored/pending_return/picked_up)
"""

from __future__ import annotations

import logging
from datetime import datetime

from app.common.enums import OrderStatus, ReportStatus, StorageStatus, WipStatus
from app.common.enums.role_d_zh import ORDER_ZH, REPORT_ZH, STORAGE_ZH, WIP_ZH
from app.common.errors import ConflictError, NotFoundError
from app.db.models import Order, StorageHistory
from app.modules.closures.repository import ClosureRepository
from app.modules.closures.serializers import storage_dict

logger = logging.getLogger(__name__)

# WIP 已結束狀態（完成或終止），對應 Role D 的 store.common.ENDED_WIP。
ENDED_WIP = {WIP_ZH[WipStatus.COMPLETED], WIP_ZH[WipStatus.TERMINATED]}

# Role D 將中止申請內嵌於 WIP，abort_status 為自由字串；待主管判定的標記值。
ABORT_PENDING = "待主管判定"


def _now() -> datetime:
    return datetime.now()


class ClosureService:
    def __init__(self, repo: ClosureRepository) -> None:
        self._repo = repo

    async def _require_order(self, order_id: str) -> Order:
        order = await self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError(f"找不到委託單：{order_id}")
        return order

    async def check_closure(self, order_id: str) -> dict:
        """結單條件檢查（result_manage.md，需全部滿足）。"""
        order = await self._require_order(order_id)
        wips = order.wips
        report_count = await self._repo.count_reports_in_status(
            order_id, [REPORT_ZH[ReportStatus.PUBLISHED], REPORT_ZH[ReportStatus.RETURNED]]
        )
        has_report = report_count > 0
        storages = await self._repo.storage_items(order_id)
        sample_ok = bool(storages) and all(
            s.status
            in (
                STORAGE_ZH[StorageStatus.STORED],
                STORAGE_ZH[StorageStatus.PENDING_RETURN],
                STORAGE_ZH[StorageStatus.PICKED_UP],
            )
            for s in storages
        )
        no_open_abort = all(w.abort_status != ABORT_PENDING for w in wips)
        all_ended = bool(wips) and all(w.status in ENDED_WIP for w in wips)
        conditions = [
            {"name": "所有實驗明細完成或終止", "ok": all_ended},
            {"name": "所有 WIP 已結束", "ok": all_ended},
            {
                "name": "數據已收集",
                "ok": all(w.result_note for w in wips if w.status == WIP_ZH[WipStatus.COMPLETED]),
            },
            {"name": "無未結異常", "ok": no_open_abort},
            {"name": "樣品已入庫或待返還", "ok": sample_ok},
            {"name": "報告已建立或已回傳", "ok": has_report},
        ]
        return {
            "orderId": order_id,
            "status": order.status,
            "canClose": all(c["ok"] for c in conditions),
            "conditions": conditions,
        }

    async def list_closures(self) -> list[dict]:
        orders = await self._repo.list_orders()
        return [await self.check_closure(o.order_id) for o in orders]

    async def list_storage(self, status: str | None = None) -> list[dict]:
        items = await self._repo.list_storage(status)
        return [storage_dict(s) for s in items]

    async def to_pickup(self, order_id: str) -> dict:
        order = await self._require_order(order_id)
        check = await self.check_closure(order_id)
        if not check["canClose"]:
            unmet = "、".join(c["name"] for c in check["conditions"] if not c["ok"])
            raise ConflictError(f"尚未滿足結單條件：{unmet}")
        if order.status not in (
            ORDER_ZH[OrderStatus.COMPLETED],
            ORDER_ZH[OrderStatus.WAITING_REPORT_RETURN],
        ):
            raise ConflictError(f"委託單為「{order.status}」，無法轉待取件")
        order.status = ORDER_ZH[OrderStatus.WAITING_PICKUP]
        await self._repo.commit()
        # NEW: pickup-reminder email (async via Celery, broker-fallback safe).
        await self._send_pickup_reminder(order)
        return {"orderId": order_id, "status": order.status}

    async def storage_inbound(self, order_id: str, operator: str | None, note: str | None) -> dict:
        items = await self._repo.storage_items(order_id)
        if not items:
            raise NotFoundError(f"委託單 {order_id} 無倉儲紀錄")
        for s in items:
            if s.status == STORAGE_ZH[StorageStatus.IN_LAB]:
                s.status = STORAGE_ZH[StorageStatus.STORED]
                s.history.append(
                    StorageHistory(
                        time=_now(), action="入庫", actor=operator or "系統", note=note or ""
                    )
                )
        await self._repo.commit()
        return {"orderId": order_id, "items": [storage_dict(s) for s in items]}

    async def storage_outbound(self, order_id: str, operator: str | None, note: str | None) -> dict:
        order = await self._require_order(order_id)
        if order.status != ORDER_ZH[OrderStatus.WAITING_PICKUP]:
            raise ConflictError(f"委託單為「{order.status}」，僅「待取件」可出庫取件")
        items = await self._repo.storage_items(order_id)
        if not items:
            raise NotFoundError(f"委託單 {order_id} 無倉儲紀錄")
        for s in items:
            s.status = STORAGE_ZH[StorageStatus.PICKED_UP]
            s.history.append(
                StorageHistory(
                    time=_now(), action="出庫取件", actor=operator or "系統", note=note or ""
                )
            )
        await self._repo.commit()
        return {"orderId": order_id, "items": [storage_dict(s) for s in items]}

    async def close_order(self, order_id: str, operator: str | None) -> dict:
        order = await self._require_order(order_id)
        if order.status != ORDER_ZH[OrderStatus.WAITING_PICKUP]:
            raise ConflictError(f"委託單為「{order.status}」，僅「待取件」可結案")
        items = await self._repo.storage_items(order_id)
        if items and not all(s.status == STORAGE_ZH[StorageStatus.PICKED_UP] for s in items):
            raise ConflictError("尚有樣品未取件，無法結案")
        order.status = ORDER_ZH[OrderStatus.CLOSED]
        await self._repo.commit()
        return {"orderId": order_id, "status": order.status}

    async def _send_pickup_reminder(self, order: Order) -> None:
        """Enqueue the pickup-reminder email; degrade gracefully if the broker is down.

        Mirrors the broker-fallback pattern in
        ``app/routers/experiments.py::machine_signal``: try ``.delay(...)`` first,
        and on any failure fall back to a synchronous send so the demo still works
        without Redis.

        TODO(recipient): ``Order.applicant`` is a display name, not an email.
        We try to resolve a real address via the users table (``find_user_email_by_name``);
        if that fails we fall back to ``"<applicant>" <noreply…>`` placeholder so the
        task is still wired. Replace this once orders carry an ``applicant_email``
        (or a FK to ``users``).
        """
        # Lazy import keeps Celery (and Redis) off the import path for tests that
        # never hit this code, and matches the experiments router's local import.
        from app.workers.email_sender import send_pickup_reminder_email

        recipient = await self._repo.find_user_email_by_name(order.applicant)
        if not recipient:
            # TODO(recipient): no resolvable email — best-effort placeholder.
            recipient = order.applicant
            logger.warning(
                "No email resolved for applicant %r on order %s; using placeholder recipient %r",
                order.applicant,
                order.order_id,
                recipient,
            )

        try:
            send_pickup_reminder_email.delay(
                to=recipient, order_id=order.order_id, applicant=order.applicant
            )
        except Exception:  # broker unavailable → synchronous fallback
            logger.warning(
                "Celery broker unavailable; sending pickup reminder synchronously for order %s",
                order.order_id,
            )
            try:
                send_pickup_reminder_email.run(
                    to=recipient, order_id=order.order_id, applicant=order.applicant
                )
            except Exception:
                logger.exception("Failed to send pickup reminder for order %s", order.order_id)
