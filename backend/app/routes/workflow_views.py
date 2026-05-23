from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.order_enums import OrderStatus
from app.core.time import utc_now
from app.schemas.order import ApiResponse, OrderItem
from app.services.dependencies import get_order_service
from app.services.order_service import OrderService

router = APIRouter(prefix="/api", tags=["Workflow Views"])


def _order_items_for(order_id: int, service: OrderService) -> list[OrderItem]:
    return service.get_order(order_id).items


@router.get("/orders/{order_id}/wips")
def get_order_wips(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    items = _order_items_for(order_id, service)
    return ApiResponse(
        data=[
            {
                "id": index + 1,
                "orderId": order_id,
                "orderItemId": item.id,
                "sampleId": item.sample_id,
                "step": "sample_received" if index == 0 else "pending",
                "progress": 20 if index == 0 else 0,
                "status": "pending",
                "updatedAt": utc_now(),
            }
            for index, item in enumerate(items)
        ]
    )


@router.get("/wips")
def list_wips(
    order_id: int | None = Query(default=None, alias="orderId"),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    if order_id is not None:
        return get_order_wips(order_id, service)

    data: list[dict[str, Any]] = []
    for order in service.list_orders():
        for item in order.items:
            data.append(
                {
                    "id": len(data) + 1,
                    "orderId": order.id,
                    "orderItemId": item.id,
                    "sampleId": item.sample_id,
                    "step": "sample_received",
                    "progress": 20,
                    "status": "pending",
                    "updatedAt": order.updated_at,
                }
            )
    return ApiResponse(data=data)


@router.get("/orders/{order_id}/reports")
def get_order_reports(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    order = service.get_order(order_id)
    data = []
    for index, item in enumerate(order.items):
        data.append(
            {
                "id": index + 1,
                "reportNo": f"RPT-{order.order_no}-{index + 1}",
                "orderId": order_id,
                "orderItemId": item.id,
                "status": "completed" if order.status == OrderStatus.CLOSED else "pending",
                "fileUrl": None,
                "createdAt": order.created_at,
                "updatedAt": order.updated_at,
            }
        )
    return ApiResponse(data=data)


@router.get("/reports")
def list_reports(
    order_id: int | None = Query(default=None, alias="orderId"),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    if order_id is not None:
        return get_order_reports(order_id, service)
    data: list[dict[str, Any]] = []
    for order in service.list_orders():
        data.extend(get_order_reports(order.id, service).data or [])
    return ApiResponse(data=data)


@router.get("/orders/{order_id}/issues")
def get_order_issues(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    order = service.get_order(order_id)
    data = []
    if order.status == OrderStatus.RETURNED and order.last_reason:
        data.append(
            {
                "id": 1,
                "orderId": order_id,
                "type": "returned_order",
                "level": "warning",
                "message": order.last_reason,
                "isResolved": False,
                "createdAt": order.updated_at,
            }
        )
    return ApiResponse(data=data)


@router.get("/issues")
def list_issues(
    order_id: int | None = Query(default=None, alias="orderId"),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    if order_id is not None:
        return get_order_issues(order_id, service)
    data: list[dict[str, Any]] = []
    for order in service.list_orders():
        data.extend(get_order_issues(order.id, service).data or [])
    return ApiResponse(data=data)
