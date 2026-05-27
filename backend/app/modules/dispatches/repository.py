"""Async DB queries for the dispatches module."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dispatch, Lab, Machine, Recipe, Wip, WipHistory


class DispatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_wip_by_no(self, wip_no: str) -> Wip | None:
        """Look up B's WIP by business code (``dispatches.wip_id`` == ``wips.wip_no``)."""
        result = await self._session.execute(select(Wip).where(Wip.wip_no == wip_no))
        return result.scalar_one_or_none()

    def add_wip_history(self, history: WipHistory) -> None:
        self._session.add(history)

    async def list_dispatches(self, lab_code: str | None = None) -> Sequence[Dispatch]:
        stmt = select(Dispatch)
        if lab_code is not None:
            stmt = stmt.where(Dispatch.lab == lab_code)
        result = await self._session.execute(stmt.order_by(Dispatch.dispatch_id))
        return result.scalars().all()

    async def list_by_statuses(
        self, statuses: Sequence[str], lab_code: str | None = None
    ) -> Sequence[Dispatch]:
        stmt = select(Dispatch).where(Dispatch.status.in_(list(statuses)))
        if lab_code is not None:
            stmt = stmt.where(Dispatch.lab == lab_code)
        result = await self._session.execute(stmt.order_by(Dispatch.dispatch_id))
        return result.scalars().all()

    async def get_by_dispatch_id(self, dispatch_id: str) -> Dispatch | None:
        result = await self._session.execute(
            select(Dispatch).where(Dispatch.dispatch_id == dispatch_id)
        )
        return result.scalar_one_or_none()

    async def list_machines(self, lab_code: str | None = None) -> Sequence[Machine]:
        stmt = select(Machine)
        if lab_code is not None:
            stmt = stmt.where(Machine.lab == lab_code)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_machine(self, machine_id: str) -> Machine | None:
        result = await self._session.execute(
            select(Machine).where(Machine.machine_id == machine_id)
        )
        return result.scalar_one_or_none()

    async def lab_code_for_name(self, lab_name: str) -> str | None:
        """Resolve a lab's display name (used by B's wips.lab_name) to its
        short code (used by C's dispatches.lab / machines.lab)."""
        result = await self._session.execute(select(Lab.code).where(Lab.name == lab_name))
        return result.scalars().first()

    async def get_recipe(self, recipe_id: str) -> Recipe | None:
        result = await self._session.execute(select(Recipe).where(Recipe.recipe_id == recipe_id))
        return result.scalar_one_or_none()

    def add(self, dispatch: Dispatch) -> None:
        self._session.add(dispatch)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
