"""FastAPI dependencies for the closures module — ClosureService factory."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.common.dependencies.lab_scope import build_lab_scope
from app.core.database import get_db
from app.modules.closures.repository import ClosureRepository
from app.modules.closures.service import ClosureService


async def get_closure_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ClosureService:
    scope = await build_lab_scope(user, session)
    return ClosureService(ClosureRepository(session), scope)
