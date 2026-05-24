from __future__ import annotations

from math import ceil
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import CurrentUser, get_current_user
from app.core.order_constants import TRANSITIONS
from app.core.order_enums import OrderStatus
from app.schemas.order import ApiResponse, OrderActionRequest, OrderCreate, OrderUpdate
from app.services.dependencies import get_order_service
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("")
async def list_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    applicant_id: str | None = Query(default=None, alias="applicantId"),
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> dict[str, Any]:
    orders = await service.list_orders(
        status_filter=status_filter,
        applicant_id=applicant_id,
        current_user=current_user,
    )
    total = len(orders)
    start = (page - 1) * limit
    end = start + limit
    return {
        "success": True,
        "data": [order.model_dump(by_alias=True) for order in orders[start:end]],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "totalPages": ceil(total / limit) if total else 0,
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    order = await service.create_order(payload, current_user)
    return ApiResponse(
        data={
            "id": order.id,
            "orderNo": order.order_no,
            "status": order.status,
            "priority": order.priority,
            "message": "委託單已建立",
        }
    )


@router.get("/applicant/{applicant_id}")
async def list_orders_by_applicant(
    applicant_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    return ApiResponse(
        data=[
            order.model_dump(by_alias=True)
            for order in await service.list_orders(
                applicant_id=applicant_id,
                current_user=current_user,
            )
        ]
    )


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    order = await service.get_order(order_id)
    return ApiResponse(data=order.model_dump(by_alias=True))


@router.patch("/{order_id}")
async def update_order(
    order_id: int,
    payload: OrderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    order = await service.update_order(order_id, payload, current_user)
    return ApiResponse(data=order.model_dump(by_alias=True), message="委託單已更新")


@router.delete("/{order_id}")
async def delete_order(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    await service.delete_order(order_id, current_user)
    return ApiResponse(data={"id": order_id}, message="委託單已刪除")


@router.post("/{order_id}/actions")
async def handle_order_action(
    order_id: int,
    payload: OrderActionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    order = await service.apply_action(order_id, payload, current_user)
    message = TRANSITIONS[payload.action][2]
    return ApiResponse(
        data={
            "id": order.id,
            "action": payload.action,
            "status": order.status,
            "quotaOverride": payload.quota_override,
        },
        message=message,
    )


@router.get("/{order_id}/history")
async def get_order_history(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    return ApiResponse(
        data=[item.model_dump(by_alias=True) for item in await service.get_history(order_id)]
    )
