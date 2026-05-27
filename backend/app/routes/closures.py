"""結案與倉儲取件 API：/api/closures。

Controller for the closures module — mounted from the central ``app/routes``
registry. Thin router; all logic lives in
:class:`app.modules.closures.service.ClosureService`.

Auth: write endpoints require ``require_permission("closures:operate")``; reads
require an authenticated user.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse, PageResponse
from app.modules.closures.dependencies import get_closure_service
from app.modules.closures.schemas import CloseStepBody
from app.modules.closures.service import ClosureService

router = APIRouter(prefix="/api/closures", tags=["Closures"])

CLOSURES_OPERATE = "closures:operate"


@router.get("", response_model=PageResponse[dict])
async def list_closures(
    service: Annotated[ClosureService, Depends(get_closure_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PageResponse[dict]:
    """列出各委託單的結單狀態與條件達成情況。"""
    items = await service.list_closures()
    return PageResponse(items=items, page=1, pageSize=len(items), total=len(items))


@router.get("/storage", response_model=PageResponse[dict])
async def list_storage(
    service: Annotated[ClosureService, Depends(get_closure_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
    status: str | None = None,
) -> PageResponse[dict]:
    """倉儲取件清單（給 /storage 頁使用）。"""
    items = await service.list_storage(status)
    return PageResponse(items=items, page=1, pageSize=len(items), total=len(items))


@router.get("/{order_id}/check", response_model=ApiResponse[dict])
async def check_closure(
    order_id: str,
    service: Annotated[ClosureService, Depends(get_closure_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[dict]:
    """結單條件檢查。"""
    return ApiResponse(data=await service.check_closure(order_id))


@router.post("/{order_id}/to-pickup", response_model=ApiResponse[dict])
async def to_pickup(
    order_id: str,
    service: Annotated[ClosureService, Depends(get_closure_service)],
    _: Annotated[CurrentUser, Depends(require_permission(CLOSURES_OPERATE))],
) -> ApiResponse[dict]:
    """轉待取件；成功後寄送取件提醒 Email（背景，broker 不可用時退回同步）。"""
    return ApiResponse(data=await service.to_pickup(order_id), message="已轉待取件")


@router.post("/{order_id}/inbound", response_model=ApiResponse[dict])
async def inbound(
    order_id: str,
    body: CloseStepBody,
    service: Annotated[ClosureService, Depends(get_closure_service)],
    _: Annotated[CurrentUser, Depends(require_permission(CLOSURES_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.storage_inbound(order_id, body.operator, body.note),
        message="樣品已入庫",
    )


@router.post("/{order_id}/outbound", response_model=ApiResponse[dict])
async def outbound(
    order_id: str,
    body: CloseStepBody,
    service: Annotated[ClosureService, Depends(get_closure_service)],
    _: Annotated[CurrentUser, Depends(require_permission(CLOSURES_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.storage_outbound(order_id, body.operator, body.note),
        message="樣品已出庫取件",
    )


@router.post("/{order_id}/close", response_model=ApiResponse[dict])
async def close_order(
    order_id: str,
    body: CloseStepBody,
    service: Annotated[ClosureService, Depends(get_closure_service)],
    _: Annotated[CurrentUser, Depends(require_permission(CLOSURES_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.close_order(order_id, body.operator),
        message="委託單已結案",
    )
