"""FastAPI dependency: MasterDataService factory."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.master_data.service import MasterDataService


def get_master_data_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MasterDataService:
    return MasterDataService(session)
