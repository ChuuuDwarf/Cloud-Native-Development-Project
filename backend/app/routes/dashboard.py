"""HTTP routes for /api/dashboard.

One endpoint. Returns a snapshot of every widget; scope is applied
server-side based on the caller's role.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, require_permission
from app.common.schemas import ApiResponse
from app.schemas.dashboard import DashboardSnapshot
from app.services.dashboard import DashboardService, get_dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=ApiResponse[DashboardSnapshot])
async def get_dashboard(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    user: Annotated[CurrentUser, Depends(require_permission("dashboard:read"))],
) -> ApiResponse[DashboardSnapshot]:
    snapshot = await service.get_snapshot(user)
    return ApiResponse(data=DashboardSnapshot.model_validate(snapshot))
