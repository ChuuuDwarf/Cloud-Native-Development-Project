from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import CurrentUser, get_current_user
from app.core.order_enums import PriorityLevel
from app.core.order_security import require_role, user_id
from app.db.models.order_management import QuotaSettingModel
from app.schemas.order import ApiResponse, QuotaPatchPayload, QuotaPayload
from app.services.dependencies import get_order_service
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/quotas", tags=["Quotas"])


async def quota_to_dict(quota: QuotaSettingModel, service: OrderService) -> dict[str, Any]:
    check = await service.check_quota(
        applicant_id=quota.scope_id if quota.scope_type == "user" else "__not_applicable__",
        department_id=quota.scope_id if quota.scope_type == "department" else "__not_applicable__",
        item_count=0,
    )
    matching = next(
        (
            item
            for item in check["checks"]
            if item["scopeType"] == quota.scope_type and item["scopeId"] == quota.scope_id
        ),
        None,
    )
    used = matching["used"] if matching else 0
    reserved = matching["reserved"] if matching else 0
    effective_used = matching["effectiveUsed"] if matching else used

    return {
        "id": quota.id,
        "scopeType": quota.scope_type,
        "scopeId": quota.scope_id,
        "monthlyLimit": quota.monthly_limit,
        "urgentLimit": quota.urgent_limit,
        "criticalLimit": quota.critical_limit,
        "isActive": quota.is_active,
        "usedCount": used,
        "reservedCount": reserved,
        "effectiveUsedCount": effective_used,
        "remaining": max(quota.monthly_limit - effective_used, 0),
    }


@router.get("")
async def list_quotas(service: OrderService = Depends(get_order_service)) -> ApiResponse:
    quotas = [
        await quota_to_dict(quota, service)
        for quota in await service.list_quota_settings()
    ]
    return ApiResponse(data=quotas)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_quota(
    payload: QuotaPayload,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    require_role(current_user, {"admin"})
    quota = await service.create_quota_setting(payload)
    return ApiResponse(data=await quota_to_dict(quota, service), message="配額設定已建立")


@router.patch("/{quota_id}")
async def update_quota(
    quota_id: int,
    payload: QuotaPatchPayload,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    require_role(current_user, {"admin"})
    quota = await service.update_quota_setting(quota_id, payload)
    return ApiResponse(data=await quota_to_dict(quota, service), message="配額設定已更新")


@router.get("/check")
async def check_quota(
    applicant_id: str | None = Query(default=None, alias="applicantId"),
    department_id: str = Query(alias="departmentId"),
    item_count: int = Query(default=1, ge=1, alias="itemCount"),
    priority: PriorityLevel = Query(default=PriorityLevel.NORMAL),
    current_user: CurrentUser = Depends(get_current_user),
    service: OrderService = Depends(get_order_service),
) -> ApiResponse:
    quota_result = await service.check_quota(
        applicant_id or user_id(current_user),
        department_id,
        item_count,
        priority.value,
    )
    return ApiResponse(data=quota_result)
