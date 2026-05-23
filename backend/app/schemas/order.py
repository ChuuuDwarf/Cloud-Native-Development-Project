from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.order_constants import MAX_ITEMS_PER_ORDER
from app.core.order_enums import OrderAction, OrderStatus, PriorityLevel


class OrderItemCreate(BaseModel):
    sample_id: str = Field(alias="sampleId", min_length=1)
    lab_id: str = Field(alias="labId", min_length=1)
    experiment_id: str = Field(alias="experimentId", min_length=1)

    model_config = {"populate_by_name": True}


class OrderItem(OrderItemCreate):
    id: int
    status: str = "draft"
    approved_by: str | None = Field(default=None, alias="approvedBy")
    approved_at: datetime | None = Field(default=None, alias="approvedAt")
    return_reason: str | None = Field(default=None, alias="returnReason")
    reject_reason: str | None = Field(default=None, alias="rejectReason")
    quota_exceeded: bool = Field(default=False, alias="quotaExceeded")
    quota_override: bool = Field(default=False, alias="quotaOverride")
    quota_override_reason: str | None = Field(default=None, alias="quotaOverrideReason")
    quota_approved_by: str | None = Field(default=None, alias="quotaApprovedBy")
    quota_approved_at: datetime | None = Field(default=None, alias="quotaApprovedAt")

    model_config = {"populate_by_name": True}


class OrderItemPatch(OrderItemCreate):
    order_item_id: int | None = Field(default=None, alias="orderItemId")

    model_config = {"populate_by_name": True}


class OrderCreate(BaseModel):
    applicant_id: str | None = Field(default=None, alias="applicantId")
    department_id: str = Field(alias="departmentId", min_length=1)
    apply_date: datetime | None = Field(default=None, alias="applyDate")
    priority: PriorityLevel | None = None
    items: list[OrderItemCreate] = Field(min_length=1, max_length=MAX_ITEMS_PER_ORDER)

    model_config = {"populate_by_name": True}


class OrderUpdate(BaseModel):
    department_id: str | None = Field(default=None, alias="departmentId")
    apply_date: datetime | None = Field(default=None, alias="applyDate")
    priority: PriorityLevel | None = None
    items: list[OrderItemPatch] | None = None

    model_config = {"populate_by_name": True}

    @field_validator("department_id")
    @classmethod
    def validate_department_id(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("departmentId cannot be empty")
        return value

    @field_validator("items")
    @classmethod
    def validate_items(
        cls,
        value: list[OrderItemCreate] | None,
    ) -> list[OrderItemCreate] | None:
        if value is not None:
            if len(value) == 0:
                raise ValueError("items must contain at least one item")
            if len(value) > MAX_ITEMS_PER_ORDER:
                raise ValueError(f"items cannot exceed {MAX_ITEMS_PER_ORDER}")
        return value

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> OrderUpdate:
        has_value = any(
            value is not None
            for value in (self.department_id, self.apply_date, self.priority, self.items)
        )
        if not has_value:
            raise ValueError("at least one update field is required")
        return self


class OrderActionRequest(BaseModel):
    action: OrderAction
    actor_id: str | None = Field(default=None, alias="actorId")
    order_item_id: int | None = Field(default=None, alias="orderItemId")
    reason: str | None = None
    quota_override: bool = Field(default=False, alias="quotaOverride")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_reason(self) -> OrderActionRequest:
        reason = self.reason.strip() if self.reason else ""
        if self.action in {OrderAction.RETURN, OrderAction.REJECT} and not reason:
            raise ValueError("return or reject action requires reason")
        if self.quota_override and self.action != OrderAction.APPROVE:
            raise ValueError("quotaOverride can only be used with approve action")
        if self.action == OrderAction.APPROVE and self.quota_override and not reason:
            raise ValueError("quotaOverride approve action requires reason")
        if self.reason is not None:
            self.reason = reason or None
        return self


class Order(BaseModel):
    id: int
    order_no: str = Field(alias="orderNo")
    applicant_id: str = Field(alias="applicantId")
    department_id: str = Field(alias="departmentId")
    apply_date: datetime = Field(alias="applyDate")
    status: OrderStatus
    priority: PriorityLevel = PriorityLevel.NORMAL
    total_items: int = Field(alias="totalItems")
    last_reason: str | None = Field(default=None, alias="lastReason")
    is_deleted: bool = Field(default=False, alias="isDeleted")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    items: list[OrderItem] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class OrderHistory(BaseModel):
    id: int
    order_id: int = Field(alias="orderId")
    actor_id: str = Field(alias="actorId")
    action: str
    from_status: str | None = Field(default=None, alias="fromStatus")
    to_status: str = Field(alias="toStatus")
    reason: str | None = None
    quota_override: bool = Field(default=False, alias="quotaOverride")
    action_time: datetime = Field(alias="actionTime")

    model_config = {"populate_by_name": True}


class ApiResponse(BaseModel):
    success: bool = True
    data: Any | None = None
    message: str | None = None


class QuotaPayload(BaseModel):
    scope_type: str = Field(alias="scopeType")
    scope_id: str = Field(alias="scopeId")
    monthly_limit: int = Field(alias="monthlyLimit", ge=0)
    urgent_limit: int | None = Field(default=None, alias="urgentLimit", ge=0)
    critical_limit: int | None = Field(default=None, alias="criticalLimit", ge=0)
    is_active: bool = Field(default=True, alias="isActive")
    actor_id: str | None = Field(default=None, alias="actorId")

    model_config = {"populate_by_name": True}


class QuotaPatchPayload(BaseModel):
    monthly_limit: int | None = Field(default=None, alias="monthlyLimit", ge=0)
    urgent_limit: int | None = Field(default=None, alias="urgentLimit", ge=0)
    critical_limit: int | None = Field(default=None, alias="criticalLimit", ge=0)
    is_active: bool | None = Field(default=None, alias="isActive")
    actor_id: str | None = Field(default=None, alias="actorId")

    model_config = {"populate_by_name": True}
