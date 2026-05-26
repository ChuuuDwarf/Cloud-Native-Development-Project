"""Async DB queries for the reports module.

Reports are D-owned (table ``reports``; ``order_id`` / ``wip_id`` columns hold
A/B business codes ``order_no`` / ``wip_no``). WIP lookups use B's ``Wip`` and
D's ``WipExecution`` side row; order lookups use A's ``OrderModel`` by
``order_no``. See [[cd-yields-to-ab-models]].
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import OrderModel, Report, ReportTemplate, Wip, WipExecution


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
        self,
        status: str | None = None,
        order_no: str | None = None,
        lab_name: str | None = None,
    ) -> Sequence[Report]:
        stmt = select(Report).options(
            selectinload(Report.versions), selectinload(Report.attachments)
        )
        if status:
            stmt = stmt.where(Report.status == status)
        if order_no:
            stmt = stmt.where(Report.order_id == order_no)
        if lab_name is not None:
            # A report's lab is the lab of its source WIP (reports.wip_id == wips.wip_no).
            stmt = stmt.join(Wip, Report.wip_id == Wip.wip_no).where(Wip.lab_name == lab_name)
        result = await self._session.execute(stmt)
        return result.scalars().unique().all()

    async def count_reports_for_order(self, order_no: str) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(Report).where(Report.order_id == order_no)
        )
        return result.scalar_one()

    async def count_formal_reports_for_wip(self, wip_no: str, statuses: list[str]) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.wip_id == wip_no, Report.status.in_(statuses))
        )
        return result.scalar_one()

    async def get_wip(self, wip_no: str) -> Wip | None:
        result = await self._session.execute(select(Wip).where(Wip.wip_no == wip_no))
        return result.scalar_one_or_none()

    async def get_exec(self, wip_no: str) -> WipExecution | None:
        return await self._session.get(WipExecution, wip_no)

    async def get_order(self, order_no: str) -> OrderModel | None:
        result = await self._session.execute(
            select(OrderModel).where(OrderModel.order_no == order_no)
        )
        return result.scalar_one_or_none()

    async def add(self, obj) -> None:
        self._session.add(obj)

    async def list_templates(self) -> Sequence[ReportTemplate]:
        result = await self._session.execute(
            select(ReportTemplate).order_by(ReportTemplate.created_at.desc())
        )
        return result.scalars().all()

    async def get_template(self, template_id: int) -> ReportTemplate | None:
        return await self._session.get(ReportTemplate, template_id)

    async def commit(self) -> None:
        await self._session.commit()
