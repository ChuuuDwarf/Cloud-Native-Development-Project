"""Async DB queries for the experiment-runs module.

All relationship access is eager-loaded with ``selectinload`` so the service
never touches a lazy attribute on an ``AsyncSession``.

Ported from Role D's flat ``app/store/experiments.py`` + ``common.py`` DB access.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Order, Wip


class ExperimentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_wip(self, wip_id: str) -> Wip | None:
        """Load one WIP with history and order (+ order.wips) eager-loaded."""
        result = await self._session.execute(
            select(Wip)
            .options(
                selectinload(Wip.history),
                selectinload(Wip.order).selectinload(Order.wips),
            )
            .where(Wip.wip_id == wip_id)
        )
        return result.scalar_one_or_none()

    async def list_wips(self, status: str | None = None) -> Sequence[Wip]:
        stmt = select(Wip).options(
            selectinload(Wip.history),
            selectinload(Wip.order),
        )
        if status:
            stmt = stmt.where(Wip.status == status)
        result = await self._session.execute(stmt)
        return result.scalars().unique().all()

    async def get_wip_by_id(self, wip_id: str) -> Wip | None:
        """Lightweight fetch (no eager-load) for background tasks."""
        return await self._session.get(Wip, wip_id)

    async def commit(self) -> None:
        await self._session.commit()
