"""Async DB queries for the dispatches module."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dispatch, Machine, Recipe


class DispatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_dispatches(self) -> Sequence[Dispatch]:
        result = await self._session.execute(select(Dispatch).order_by(Dispatch.dispatch_id))
        return result.scalars().all()

    async def list_by_statuses(self, statuses: Sequence[str]) -> Sequence[Dispatch]:
        result = await self._session.execute(
            select(Dispatch)
            .where(Dispatch.status.in_(list(statuses)))
            .order_by(Dispatch.dispatch_id)
        )
        return result.scalars().all()

    async def get_by_dispatch_id(self, dispatch_id: str) -> Dispatch | None:
        result = await self._session.execute(
            select(Dispatch).where(Dispatch.dispatch_id == dispatch_id)
        )
        return result.scalar_one_or_none()

    async def list_machines(self) -> Sequence[Machine]:
        result = await self._session.execute(select(Machine))
        return result.scalars().all()

    async def get_machine(self, machine_id: str) -> Machine | None:
        result = await self._session.execute(
            select(Machine).where(Machine.machine_id == machine_id)
        )
        return result.scalar_one_or_none()

    async def get_recipe(self, recipe_id: str) -> Recipe | None:
        result = await self._session.execute(select(Recipe).where(Recipe.recipe_id == recipe_id))
        return result.scalar_one_or_none()

    def add(self, dispatch: Dispatch) -> None:
        self._session.add(dispatch)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
