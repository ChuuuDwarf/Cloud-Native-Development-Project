"""RoleService — read-only listing in Phase 1; CRUD lands in Phase 6 (stretch)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.db.models import Permission, Role


class RoleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_roles(self) -> list[Role]:
        result = await self._session.execute(
            select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
        )
        return list(result.scalars().all())

    async def list_permissions(self) -> list[Permission]:
        result = await self._session.execute(select(Permission).order_by(Permission.code))
        return list(result.scalars().all())


def get_role_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RoleService:
    return RoleService(session)
