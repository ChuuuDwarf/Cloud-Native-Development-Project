"""FastAPI dependencies for the closures module — ClosureService factory."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.closures.repository import ClosureRepository
from app.modules.closures.service import ClosureService


def get_closure_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ClosureService:
    return ClosureService(ClosureRepository(session))
