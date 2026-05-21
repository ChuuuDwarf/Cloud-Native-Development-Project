"""FastAPI dependency: RoleService factory."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.roles.service import RoleService


def get_role_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RoleService:
    return RoleService(session)
