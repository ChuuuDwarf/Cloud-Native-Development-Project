"""FastAPI dependencies for the dispatches module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.dispatches.repository import DispatchRepository
from app.modules.dispatches.service import DispatchService


def get_dispatch_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DispatchService:
    return DispatchService(DispatchRepository(session))
