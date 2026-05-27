"""Async DB queries for the experiment-runs module.

D's experiment execution now spans two tables:

- B's ``wips`` (canonical sample-flow row; coarse English ``status``) — see
  :mod:`app.db.models.wips`.
- D's ``wip_execution`` side table (fine-grained ``exec_status`` + machine /
  result / abort fields), keyed 1:1 by the business code ``wip_no``.

There is no ORM relationship between the two (B uses a UUID PK; we join on
``wip_no``), so callers fetch the pair explicitly. Order lookups use A's
``OrderModel`` by business code ``order_no``. See [[cd-yields-to-ab-models]].
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import WipStatus
from app.db.models import Dispatch, Lab, OrderModel, Role, User, Wip, WipExecution


class ExperimentRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Raw session — used to hand off to B's sample-flow helpers."""
        return self._session

    async def get_wip(self, wip_no: str) -> Wip | None:
        """Load one WIP (B) with history eager-loaded."""
        result = await self._session.execute(
            select(Wip).options(selectinload(Wip.history)).where(Wip.wip_no == wip_no)
        )
        return result.scalar_one_or_none()

    async def list_wips(self, lab_name: str | None = None) -> Sequence[Wip]:
        """List WIPs (B) with history; optionally restricted to one ``lab_name``."""
        stmt = select(Wip).options(selectinload(Wip.history))
        if lab_name is not None:
            stmt = stmt.where(Wip.lab_name == lab_name)
        result = await self._session.execute(stmt)
        return result.scalars().unique().all()

    async def get_exec(self, wip_no: str) -> WipExecution | None:
        return await self._session.get(WipExecution, wip_no)

    async def get_dispatch_assignment(self, wip_no: str) -> tuple[str | None, str | None]:
        """The (machine, recipe) C 已指派 for this WIP (``dispatches.wip_id``)."""
        return (await self.get_dispatch_assignments([wip_no])).get(wip_no, (None, None))

    async def get_dispatch_assignments(
        self, wip_nos: Sequence[str]
    ) -> dict[str, tuple[str | None, str | None]]:
        """Bulk map ``wip_no -> (assigned_machine_id, assigned_recipe_id)``.

        Lets the experiment-runs view pre-fill the planned machine/Recipe for a
        待上機 WIP (assignment lives in C's ``dispatches``, not yet on the WIP).
        Only dispatches that carry an assignment are returned.
        """
        if not wip_nos:
            return {}
        result = await self._session.execute(
            select(
                Dispatch.wip_id,
                Dispatch.assigned_machine_id,
                Dispatch.assigned_recipe_id,
            ).where(
                Dispatch.wip_id.in_(wip_nos),
                Dispatch.assigned_machine_id.is_not(None),
            )
        )
        return {row.wip_id: (row.assigned_machine_id, row.assigned_recipe_id) for row in result}

    async def get_execs_map(self, wip_nos: Sequence[str]) -> dict[str, WipExecution]:
        """Bulk-load execution rows for a set of WIPs, keyed by ``wip_no``."""
        if not wip_nos:
            return {}
        result = await self._session.execute(
            select(WipExecution).where(WipExecution.wip_no.in_(wip_nos))
        )
        return {e.wip_no: e for e in result.scalars().all()}

    async def ensure_exec(self, wip_no: str) -> WipExecution:
        """Get the execution row, creating a default ``waiting_load`` one if absent."""
        exec_row = await self._session.get(WipExecution, wip_no)
        if exec_row is None:
            exec_row = WipExecution(wip_no=wip_no, exec_status=WipStatus.WAITING_LOAD.value)
            self._session.add(exec_row)
        return exec_row

    async def list_lab_operators(self, lab_name: str) -> list[tuple[str, str]]:
        """Active users in ``lab_name`` whose role is engineer/supervisor.

        Returns ``(user_name, role_name)`` pairs — for the 上機 operator picker.
        ``wips.lab_name`` stores ``labs.name``; roles are the m2m ``user_roles``.
        """
        result = await self._session.execute(
            select(User.name, Role.name)
            .join(User.roles)
            .join(Lab, User.lab_id == Lab.id)
            .where(
                Lab.name == lab_name,
                User.is_active.is_(True),
                Role.name.in_(["lab_engineer", "lab_supervisor"]),
            )
            .order_by(User.name)
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_order(self, order_no: str) -> OrderModel | None:
        result = await self._session.execute(
            select(OrderModel).where(OrderModel.order_no == order_no)
        )
        return result.scalar_one_or_none()

    async def list_wips_for_order(self, order_no: str) -> Sequence[Wip]:
        result = await self._session.execute(select(Wip).where(Wip.order_no == order_no))
        return result.scalars().all()

    async def commit(self) -> None:
        await self._session.commit()
