"""Async DB queries for the closures module.

Closures reads across owners: A's ``OrderModel`` (by ``order_no``), B's ``Wip``
+ D's ``WipExecution`` side row (execution / abort state), D's ``reports`` and
``storage`` tables, and E's ``users`` (applicant email). There is no
``order.wips`` relationship (cross-owner, no FK) — WIPs are loaded by
``order_no``. See [[cd-yields-to-ab-models]].
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import OrderItemModel, OrderModel, Report, Storage, User, Wip, WipExecution


class ClosureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_order(self, order_no: str) -> OrderModel | None:
        result = await self._session.execute(
            select(OrderModel).where(OrderModel.order_no == order_no)
        )
        return result.scalar_one_or_none()

    async def list_orders(self, lab_name: str | None = None) -> Sequence[OrderModel]:
        """List orders; optionally only those with a WIP in ``lab_name``."""
        stmt = select(OrderModel)
        if lab_name is not None:
            stmt = (
                stmt.join(Wip, Wip.order_no == OrderModel.order_no)
                .where(Wip.lab_name == lab_name)
                .distinct()
            )
        result = await self._session.execute(stmt)
        return result.scalars().unique().all()

    async def order_labs(self, order_no: str) -> set[str]:
        """Distinct lab names of the order's WIPs (used for lab scoping)."""
        result = await self._session.execute(select(Wip.lab_name).where(Wip.order_no == order_no))
        return {lab for lab in result.scalars().all() if lab}

    async def list_wips_for_order(self, order_no: str) -> Sequence[Wip]:
        result = await self._session.execute(select(Wip).where(Wip.order_no == order_no))
        return result.scalars().all()

    async def list_wips_for_order_and_lab(self, order_no: str, lab_name: str) -> Sequence[Wip]:
        """Cross-lab closure: each lab only sees its own WIPs when checking
        closure conditions / marking them as closed. ``lab_name`` is the
        Chinese display name (matches ``Wip.lab_name``)."""
        result = await self._session.execute(
            select(Wip).where(Wip.order_no == order_no, Wip.lab_name == lab_name)
        )
        return result.scalars().all()

    async def all_wips_lab_closed(self, order_no: str) -> bool:
        """True iff (a) every order_item on the order has been claimed
        (``dependency_check=true``) AND (b) every WIP on the order has
        ``lab_closed=True``.

        Why the order_items gate matters
        --------------------------------
        WIPs are NOT seeded up-front for every order_item — they're created
        on-demand inside ``sample_service._split_sample`` as each downstream
        lab actually receives the sample. So for a multi-lab dependency
        chain (e.g. LAB-A -> LAB-B), LAB-A closes its WIP before LAB-B's
        WIP even exists, and the old ``COUNT(wips) == COUNT(closed)``
        check fires prematurely -> the order jumps to WAITING_PICKUP while
        LAB-B's work hasn't happened yet.

        The contract for "all the work is done" lives in ``order_items``:
        every row's ``dependency_check`` must be True (= a destination
        lab has been assigned for it). We short-circuit on the
        order_items count first to keep the cheaper query in front.

        Schema note
        -----------
        ``order_items.order_id`` is the FK to ``orders.id``; ``order_no``
        lives on ``orders``, not ``order_items``. We join via the FK
        rather than denormalising.
        """
        # Condition 1 — every order_item must be claimed.
        unclaimed = (
            await self._session.execute(
                select(func.count())
                .select_from(OrderItemModel)
                .join(OrderModel, OrderModel.id == OrderItemModel.order_id)
                .where(OrderModel.order_no == order_no)
                .where(OrderItemModel.dependency_check.is_(False))
            )
        ).scalar_one()
        if unclaimed > 0:
            return False

        # Condition 2 — every existing WIP must be lab_closed, and at least
        # one WIP must exist (an order with zero WIPs hasn't started yet).
        total = (
            await self._session.execute(
                select(func.count()).select_from(Wip).where(Wip.order_no == order_no)
            )
        ).scalar_one()
        if total == 0:
            return False
        closed = (
            await self._session.execute(
                select(func.count())
                .select_from(Wip)
                .where(Wip.order_no == order_no, Wip.lab_closed.is_(True))
            )
        ).scalar_one()
        return closed == total

    async def count_returned_reports_per_wip(self, order_no: str) -> dict[str, int]:
        """For the closure ``has_report`` gate: per-WIP count of RETURNED
        reports. Used to verify EVERY WIP has a published report — not just
        that the order has at least one (Phase L review #2 fix)."""
        from app.common.enums import ReportStatus
        from app.common.enums.role_d_zh import REPORT_ZH

        rows = (
            await self._session.execute(
                select(Report.wip_id, func.count())
                .where(
                    Report.order_id == order_no,
                    Report.status == REPORT_ZH[ReportStatus.RETURNED],
                )
                .group_by(Report.wip_id)
            )
        ).all()
        return {row[0]: int(row[1]) for row in rows}

    async def get_execs_map(self, wip_nos: Sequence[str]) -> dict[str, WipExecution]:
        if not wip_nos:
            return {}
        result = await self._session.execute(
            select(WipExecution).where(WipExecution.wip_no.in_(wip_nos))
        )
        return {e.wip_no: e for e in result.scalars().all()}

    async def count_reports_in_status(self, order_no: str, statuses: list[str]) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.order_id == order_no, Report.status.in_(statuses))
        )
        return result.scalar_one()

    async def storage_items(self, order_no: str) -> list[Storage]:
        result = await self._session.execute(
            select(Storage)
            .options(selectinload(Storage.history))
            .where(Storage.order_id == order_no)
        )
        return list(result.scalars().unique().all())

    async def sample_statuses(self, order_no: str) -> list[str]:
        """B-owned ``samples`` is raw-SQL (no ORM model); read its statuses directly.

        Used by the closure check to gate on the sample having been delivered
        onward, instead of D's ``storage`` table (which no flow populates).
        """
        result = await self._session.execute(
            text("SELECT status FROM samples WHERE order_no = :order_no"),
            {"order_no": order_no},
        )
        return [row[0] for row in result.all()]

    async def list_storage(
        self, status: str | None = None, lab_name: str | None = None
    ) -> list[Storage]:
        stmt = select(Storage).options(selectinload(Storage.history))
        if status:
            stmt = stmt.where(Storage.status == status)
        if lab_name is not None:
            # Storage rows are keyed by order_no (Storage.order_id); a storage
            # row's lab is the lab of the order's WIPs.
            stmt = (
                stmt.join(Wip, Wip.order_no == Storage.order_id)
                .where(Wip.lab_name == lab_name)
                .distinct()
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def find_user_email_by_applicant(self, applicant_id: str) -> str | None:
        """Best-effort resolve the applicant's email from ``users``.

        A's ``OrderModel.applicant_id`` is expected to hold the user's UUID. If it
        is not a UUID (or no user matches) we return ``None`` and the caller falls
        back to a placeholder recipient. See [[cd-yields-to-ab-models]].
        """
        try:
            uid = uuid.UUID(applicant_id)
        except (ValueError, AttributeError, TypeError):
            return None
        result = await self._session.execute(select(User.email).where(User.id == uid))
        return result.scalars().first()

    async def commit(self) -> None:
        await self._session.commit()
