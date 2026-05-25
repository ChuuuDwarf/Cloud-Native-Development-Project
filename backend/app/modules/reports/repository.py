"""Async DB queries for the reports module.

Ported from Role D's ``app/store/reports.py`` DB access.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Order, Report, Wip


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_report(self, report_id: str) -> Report | None:
        result = await self._session.execute(
            select(Report)
            .options(selectinload(Report.versions), selectinload(Report.attachments))
            .where(Report.report_id == report_id)
        )
        return result.scalar_one_or_none()

    async def list_reports(
        self, status: str | None = None, order_id: str | None = None
    ) -> Sequence[Report]:
        stmt = select(Report).options(
            selectinload(Report.versions), selectinload(Report.attachments)
        )
        if status:
            stmt = stmt.where(Report.status == status)
        if order_id:
            stmt = stmt.where(Report.order_id == order_id)
        result = await self._session.execute(stmt)
        return result.scalars().unique().all()

    async def count_reports_for_order(self, order_id: str) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Report).where(Report.order_id == order_id)
        )
        return result.scalar_one()

    async def get_wip(self, wip_id: str) -> Wip | None:
        result = await self._session.execute(
            select(Wip).options(selectinload(Wip.order)).where(Wip.wip_id == wip_id)
        )
        return result.scalar_one_or_none()

    async def get_order(self, order_id: str) -> Order | None:
        return await self._session.get(Order, order_id)

    async def add(self, obj) -> None:
        self._session.add(obj)

    async def commit(self) -> None:
        await self._session.commit()
