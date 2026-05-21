"""HTTP routes for /api/master-data — shared dropdowns for all frontend pages."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user
from app.common.schemas import ApiResponse
from app.modules.master_data.dependencies import get_master_data_service
from app.modules.master_data.service import MasterDataService

router = APIRouter(prefix="/api/master-data", tags=["MasterData"])


@router.get("", response_model=ApiResponse[dict])
async def get_master_data(
    service: Annotated[MasterDataService, Depends(get_master_data_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[dict]:
    payload = await service.gather()
    return ApiResponse(data=payload)
