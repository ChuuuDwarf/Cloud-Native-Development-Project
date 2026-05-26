"""FastAPI dependencies for the machines module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.common.dependencies.lab_scope import build_lab_scope
from app.core.database import get_db
from app.modules.machines.repository import MachineRepository
from app.modules.machines.service import MachineService


async def get_machine_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MachineService:
    scope = await build_lab_scope(user, session)
    return MachineService(MachineRepository(session), scope)
