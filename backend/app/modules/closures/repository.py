"""Async DB queries for the closures module.

All relationship access is eager-loaded with ``selectinload`` so the service
never touches a lazy attribute on an ``AsyncSession`` (which would raise under
async). Ported from Role D's flat ``app/store/closures.py`` + ``common.py`` DB
access, converted from sync ``Session`` to ``AsyncSession``.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Order, Report, Storage, User


class ClosureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_order(self, order_id: str) -> Order | None:
        """Load one order with its WIPs eager-loaded (no lazy access)."""
        result = await self._session.execute(
            select(Order).options(selectinload(Order.wips)).where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def list_orders(self) -> Sequence[Order]:
        result = await self._session.execute(select(Order).options(selectinload(Order.wips)))
        return result.scalars().unique().all()

    async def count_reports_in_status(self, order_id: str, statuses: list[str]) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.order_id == order_id, Report.status.in_(statuses))
        )
        return result.scalar_one()

    async def storage_items(self, order_id: str) -> list[Storage]:
        result = await self._session.execute(
            select(Storage)
            .options(selectinload(Storage.history))
            .where(Storage.order_id == order_id)
        )
        return list(result.scalars().unique().all())

    async def list_storage(self, status: str | None = None) -> list[Storage]:
        stmt = select(Storage).options(selectinload(Storage.history))
        if status:
            stmt = stmt.where(Storage.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def find_user_email_by_name(self, name: str) -> str | None:
        """Best-effort resolve an applicant's email from the users table by name.

        Role D's ``Order.applicant`` is a display name, not an email; this is the
        only available bridge to a real address. Returns ``None`` if no user (or
        more than one user) matches the name.
        """
        result = await self._session.execute(select(User.email).where(User.name == name))
        return result.scalars().first()

    async def commit(self) -> None:
        await self._session.commit()
