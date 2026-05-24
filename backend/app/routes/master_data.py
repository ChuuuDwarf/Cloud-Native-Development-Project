"""HTTP routes for /api/master-data — shared dropdowns for all frontend pages."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.common.schemas import ApiResponse
from app.core.database import get_db
from app.services.master_data import MasterDataService

router = APIRouter(prefix="/api/master-data", tags=["MasterData"])


@router.get("", response_model=ApiResponse[dict])
async def get_master_data(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[dict]:
    service = MasterDataService(session)
    payload = await service.gather()
    return ApiResponse(data=payload)
