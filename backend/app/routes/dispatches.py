"""HTTP routes for /api/dispatches. Owned by 組員 C.

Controller mounted from the central ``app/routes`` registry. Thin router; all
logic lives in :class:`app.modules.dispatches.service.DispatchService`. Matches
the frontend client ``frontend/src/services/dispatches-api.ts``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse, PageResponse
from app.modules.dispatches.dependencies import get_dispatch_service
from app.modules.dispatches.schemas import (
    AssignDispatchPayload,
    CreateDispatchPayload,
    ReplanBody,
    SuggestBody,
)
from app.modules.dispatches.service import DispatchService

router = APIRouter(prefix="/api/dispatches", tags=["Dispatches"])

DISPATCHES_READ = "dispatches:read"
DISPATCHES_MANAGE = "dispatches:manage"


@router.get("", response_model=PageResponse[dict])
async def list_dispatches(
    service: Annotated[DispatchService, Depends(get_dispatch_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PageResponse[dict]:
    items = await service.list_dispatches()
    return PageResponse(items=items, page=1, pageSize=len(items), total=len(items))


@router.post("", response_model=ApiResponse[dict])
async def create_dispatch(
    body: CreateDispatchPayload,
    service: Annotated[DispatchService, Depends(get_dispatch_service)],
    user: Annotated[CurrentUser, Depends(require_permission(DISPATCHES_MANAGE))],
) -> ApiResponse[dict]:
    return ApiResponse(data=await service.create(body, user.name), message="派工單已建立")


@router.post("/suggest", response_model=ApiResponse[list[dict]])
async def suggest_dispatches(
    body: SuggestBody,
    service: Annotated[DispatchService, Depends(get_dispatch_service)],
    _: Annotated[CurrentUser, Depends(require_permission(DISPATCHES_MANAGE))],
) -> ApiResponse[list[dict]]:
    return ApiResponse(data=await service.suggest(body.strategy), message="已產生排程建議")


@router.post("/replan", response_model=ApiResponse[list[dict]])
async def replan_dispatches(
    body: ReplanBody,
    service: Annotated[DispatchService, Depends(get_dispatch_service)],
    _: Annotated[CurrentUser, Depends(require_permission(DISPATCHES_MANAGE))],
) -> ApiResponse[list[dict]]:
    return ApiResponse(
        data=await service.replan(body.reason, body.strategy),
        message="已重新排程",
    )


@router.post("/{dispatch_id}/assign", response_model=ApiResponse[dict])
async def assign_dispatch(
    dispatch_id: str,
    body: AssignDispatchPayload,
    service: Annotated[DispatchService, Depends(get_dispatch_service)],
    user: Annotated[CurrentUser, Depends(require_permission(DISPATCHES_MANAGE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.assign(dispatch_id, body, user.name),
        message="已指派機台，狀態轉「待上機」",
    )
