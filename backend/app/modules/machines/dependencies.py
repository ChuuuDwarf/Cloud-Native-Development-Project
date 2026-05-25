"""FastAPI dependencies for the machines module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.machines.repository import MachineRepository
from app.modules.machines.service import MachineService


def get_machine_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MachineService:
    return MachineService(MachineRepository(session))
