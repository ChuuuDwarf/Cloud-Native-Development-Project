"""Async DB queries for the machines module."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Machine


class MachineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_machines(self, lab_name: str | None = None) -> Sequence[Machine]:
        stmt = select(Machine)
        if lab_name is not None:
            stmt = stmt.where(Machine.lab == lab_name)
        result = await self._session.execute(stmt.order_by(Machine.machine_id))
        return result.scalars().all()

    async def get_by_machine_id(self, machine_id: str) -> Machine | None:
        result = await self._session.execute(
            select(Machine).where(Machine.machine_id == machine_id)
        )
        return result.scalar_one_or_none()

    def add(self, machine: Machine) -> None:
        self._session.add(machine)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
