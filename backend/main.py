from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from math import ceil
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from database import Base, engine, get_db
from models import OrderHistoryModel, OrderItemModel, OrderModel, QuotaSettingModel, QuotaUsageModel

MAX_ITEMS_PER_ORDER = 10

USERS: dict[str, dict[str, Any]] = {
    "user001": {"name": "廠區使用者", "role": "site_user", "departmentId": "D001", "labIds": []},
    "manager001": {"name": "LAB001/LAB002 主管", "role": "lab_manager", "departmentId": None, "labIds": ["LAB001", "LAB002"]},
    "manager003": {"name": "LAB003 主管", "role": "lab_manager", "departmentId": None, "labIds": ["LAB003"]},
    "labstaff001": {"name": "實驗室人員", "role": "lab_staff", "departmentId": None, "labIds": ["LAB001", "LAB002", "LAB003"]},
    "admin001": {"name": "系統管理者", "role": "admin", "departmentId": None, "labIds": []},
}

DEPARTMENTS: list[dict[str, str]] = [
    {"id": "D001", "name": "製造一部"},
    {"id": "D002", "name": "品保部"},
    {"id": "D003", "name": "研發部"},
]

LABS: list[dict[str, str]] = [
    {"id": "LAB001", "name": "可靠度實驗室"},
    {"id": "LAB002", "name": "材料分析實驗室"},
    {"id": "LAB003", "name": "顯微分析實驗室"},
]

EXPERIMENTS: list[dict[str, str]] = [
    {"id": "EXP001", "name": "溫濕度測試", "labId": "LAB001"},
    {"id": "EXP002", "name": "壽命測試", "labId": "LAB001"},
    {"id": "EXP003", "name": "成分分析", "labId": "LAB002"},
    {"id": "EXP004", "name": "SEM 分析", "labId": "LAB003"},
]

DEPARTMENT_IDS = {item["id"] for item in DEPARTMENTS}
LAB_IDS = {item["id"] for item in LABS}
EXPERIMENT_BY_ID = {item["id"]: item for item in EXPERIMENTS}


def get_user(user_id: str) -> dict[str, Any]:
    user = USERS.get(user_id)
    if user is None:
        raise bad_request(f"Unknown user: {user_id}")
    return user


def require_role(user_id: str, roles: set[str]) -> dict[str, Any]:
    user = get_user(user_id)
    if user["role"] not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {user_id} does not have permission for this action",
        )
    return user


class OrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    CANCELLED = "cancelled"
    APPROVED = "approved"
    RETURNED = "returned"
    REJECTED = "rejected"
    SAMPLE_DELIVERED = "sample_delivered"
    SAMPLE_RECEIVED = "sample_received"
    READY_FOR_PICKUP = "ready_for_pickup"
    CLOSED = "closed"


class OrderAction(StrEnum):
    SUBMIT = "submit"
    CANCEL = "cancel"
    APPROVE = "approve"
    RETURN = "return"
    REJECT = "reject"
    CONFIRM_DELIVERY = "confirm_delivery"
    CONFIRM_RECEIVED = "confirm_received"
    READY_FOR_PICKUP = "ready_for_pickup"
    CLOSE = "close"


class PriorityLevel(StrEnum):
    NORMAL = "normal"
    URGENT = "urgent"
    CRITICAL = "critical"


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
    applicant_id: str = Field(alias="applicantId", min_length=1)
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


TRANSITIONS: dict[OrderAction, tuple[set[OrderStatus], OrderStatus, str]] = {
    OrderAction.SUBMIT: ({OrderStatus.DRAFT, OrderStatus.RETURNED}, OrderStatus.PENDING_APPROVAL, "委託單已送出簽核"),
    OrderAction.CANCEL: ({OrderStatus.DRAFT, OrderStatus.RETURNED, OrderStatus.PENDING_APPROVAL}, OrderStatus.CANCELLED, "委託單已取消"),
    OrderAction.APPROVE: ({OrderStatus.PENDING_APPROVAL}, OrderStatus.APPROVED, "委託單已核准"),
    OrderAction.RETURN: ({OrderStatus.PENDING_APPROVAL}, OrderStatus.RETURNED, "委託單已退回補件"),
    OrderAction.REJECT: ({OrderStatus.PENDING_APPROVAL}, OrderStatus.REJECTED, "委託單已拒絕"),
    OrderAction.CONFIRM_DELIVERY: ({OrderStatus.APPROVED}, OrderStatus.SAMPLE_DELIVERED, "已確認送樣"),
    OrderAction.CONFIRM_RECEIVED: ({OrderStatus.SAMPLE_DELIVERED}, OrderStatus.SAMPLE_RECEIVED, "已確認收樣"),
    OrderAction.READY_FOR_PICKUP: ({OrderStatus.SAMPLE_RECEIVED}, OrderStatus.READY_FOR_PICKUP, "已標記待取件"),
    OrderAction.CLOSE: ({OrderStatus.READY_FOR_PICKUP}, OrderStatus.CLOSED, "委託單已結案"),
}
FINAL_STATUSES = {OrderStatus.CLOSED, OrderStatus.REJECTED, OrderStatus.CANCELLED}
EDITABLE_STATUSES = {OrderStatus.DRAFT, OrderStatus.RETURNED}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def generate_order_no(order_id: int) -> str:
    date_text = _now().strftime("%Y%m%d")
    suffix = f"{order_id:03d}-{uuid4().hex[:4].upper()}"
    return f"ORD-{date_text}-{suffix}"


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def validate_order_master_data(department_id: str, items: list[OrderItemCreate]) -> None:
    if department_id not in DEPARTMENT_IDS:
        raise bad_request(f"Unknown department: {department_id}")

    for index, item in enumerate(items, start=1):
        if item.lab_id not in LAB_IDS:
            raise bad_request(f"Unknown lab in item {index}: {item.lab_id}")

        experiment = EXPERIMENT_BY_ID.get(item.experiment_id)

        if experiment is None:
            raise bad_request(f"Unknown experiment in item {index}: {item.experiment_id}")

        if experiment["labId"] != item.lab_id:
            raise bad_request(
                f"Experiment {item.experiment_id} does not belong to lab {item.lab_id}"
            )


def _item_to_schema(item: OrderItemModel) -> OrderItem:
    return OrderItem(
        id=item.id,
        sampleId=item.sample_id,
        labId=item.lab_id,
        experimentId=item.experiment_id,
        status=item.status,
        approvedBy=item.approved_by,
        approvedAt=item.approved_at,
        returnReason=item.return_reason,
        rejectReason=item.reject_reason,
        quotaExceeded=item.quota_exceeded,
        quotaOverride=item.quota_override,
        quotaOverrideReason=item.quota_override_reason,
        quotaApprovedBy=item.quota_approved_by,
        quotaApprovedAt=item.quota_approved_at,
    )


def _order_to_schema(order: OrderModel) -> Order:
    return Order(
        id=order.id,
        orderNo=order.order_no,
        applicantId=order.applicant_id,
        departmentId=order.department_id,
        applyDate=order.apply_date,
        status=OrderStatus(order.status),
        priority=PriorityLevel(order.priority),
        totalItems=order.total_items,
        lastReason=order.last_reason,
        isDeleted=order.is_deleted,
        createdAt=order.created_at,
        updatedAt=order.updated_at,
        items=[_item_to_schema(item) for item in order.items],
    )


def _history_to_schema(history: OrderHistoryModel) -> OrderHistory:
    return OrderHistory(
        id=history.id,
        orderId=history.order_id,
        actorId=history.actor_id,
        action=history.action,
        fromStatus=history.from_status,
        toStatus=history.to_status,
        reason=history.reason,
        quotaOverride=history.quota_override,
        actionTime=history.action_time,
    )


class QuotaPayload(BaseModel):
    scope_type: str = Field(alias="scopeType")
    scope_id: str = Field(alias="scopeId")
    monthly_limit: int = Field(alias="monthlyLimit", ge=0)
    urgent_limit: int | None = Field(default=None, alias="urgentLimit", ge=0)
    critical_limit: int | None = Field(default=None, alias="criticalLimit", ge=0)
    is_active: bool = Field(default=True, alias="isActive")
    actor_id: str = Field(default="admin001", alias="actorId")

    model_config = {"populate_by_name": True}


class QuotaPatchPayload(BaseModel):
    monthly_limit: int | None = Field(default=None, alias="monthlyLimit", ge=0)
    urgent_limit: int | None = Field(default=None, alias="urgentLimit", ge=0)
    critical_limit: int | None = Field(default=None, alias="criticalLimit", ge=0)
    is_active: bool | None = Field(default=None, alias="isActive")
    actor_id: str = Field(default="admin001", alias="actorId")

    model_config = {"populate_by_name": True}


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_order(self, payload: OrderCreate) -> Order:
        require_role(payload.applicant_id, {"site_user"})
        validate_order_master_data(payload.department_id, payload.items)

        now = _now()
        order = OrderModel(
            order_no=f"PENDING-{uuid4().hex}",
            applicant_id=payload.applicant_id,
            department_id=payload.department_id,
            apply_date=payload.apply_date or now,
            status=OrderStatus.DRAFT.value,
            priority=(payload.priority or PriorityLevel.NORMAL).value,
            total_items=len(payload.items),
            created_at=now,
            updated_at=now,
        )
        order.items = [self._make_item(item, now) for item in payload.items]
        self.db.add(order)
        self.db.flush()

        order.order_no = generate_order_no(order.id)
        self._append_history(
            order=order,
            actor_id=payload.applicant_id,
            action="create",
            from_status=None,
            to_status=OrderStatus.DRAFT.value,
        )
        self.db.commit()
        return self.get_order(order.id)

    def list_orders(
        self,
        status_filter: OrderStatus | None = None,
        applicant_id: str | None = None,
    ) -> list[Order]:
        stmt = (
            select(OrderModel)
            .options(joinedload(OrderModel.items))
            .where(OrderModel.is_deleted.is_(False))
            .order_by(OrderModel.created_at.desc())
        )
        if status_filter is not None:
            stmt = stmt.where(OrderModel.status == status_filter.value)
        if applicant_id:
            stmt = stmt.where(OrderModel.applicant_id == applicant_id)
        orders = self.db.execute(stmt).unique().scalars().all()
        return [_order_to_schema(order) for order in orders]

    def get_order(self, order_id: int) -> Order:
        return _order_to_schema(self._get_order_model(order_id))

    def update_order(self, order_id: int, payload: OrderUpdate) -> Order:
        now = _now()
        order = self._get_order_model(order_id)
        require_role(order.applicant_id, {"site_user"})

        if OrderStatus(order.status) not in EDITABLE_STATUSES:
            raise bad_request("Only draft or returned orders can be edited")

        next_department_id = payload.department_id if payload.department_id is not None else order.department_id

        if payload.items is not None:
            next_items = payload.items
        else:
            next_items = [
                OrderItemCreate(
                    sampleId=item.sample_id,
                    labId=item.lab_id,
                    experimentId=item.experiment_id,
                )
                for item in order.items
            ]

        validate_order_master_data(next_department_id, next_items)

        if payload.department_id is not None:
            order.department_id = payload.department_id
        if payload.apply_date is not None:
            order.apply_date = payload.apply_date
        if payload.priority is not None:
            order.priority = payload.priority.value
        if payload.items is not None:
            # Support partial item updates: if an item includes orderItemId, update that existing
            # returned order item only (reset status to draft and clear reasons). Otherwise
            # replace full item list (existing behavior).
            if any(getattr(item, "order_item_id", None) for item in payload.items):
                for item_patch in payload.items:
                    if item_patch.order_item_id is None:
                        continue
                    # find matching item
                    target = next((it for it in order.items if it.id == item_patch.order_item_id), None)
                    if target is None:
                        raise not_found("Order item not found")
                    # only allow editing returned items
                    if target.status != OrderStatus.RETURNED.value:
                        raise bad_request("Only returned order items can be edited individually")

                    # validate mapping for new lab/experiment
                    validate_order_master_data(order.department_id, [OrderItemCreate(sampleId=item_patch.sample_id, labId=item_patch.lab_id, experimentId=item_patch.experiment_id)])

                    target.sample_id = item_patch.sample_id
                    target.lab_id = item_patch.lab_id
                    target.experiment_id = item_patch.experiment_id
                    target.status = OrderStatus.DRAFT.value
                    target.return_reason = None
                    target.reject_reason = None
                    target.approved_by = None
                    target.approved_at = None
                    target.quota_override = False
                    target.quota_override_reason = None
                    target.quota_approved_by = None
                    target.quota_approved_at = None
                    target.updated_at = now
                order.total_items = len(order.items)
            else:
                order.items.clear()
                self.db.flush()
                order.items = [self._make_item(item, now) for item in payload.items]
                order.total_items = len(order.items)

        order.updated_at = now
        self._append_history(
            order=order,
            actor_id=order.applicant_id,
            action="update",
            from_status=order.status,
            to_status=order.status,
        )
        self.db.commit()
        return self.get_order(order.id)

    def delete_order(self, order_id: int) -> None:
        now = _now()
        order = self._get_order_model(order_id)
        require_role(order.applicant_id, {"site_user"})
        if order.status != OrderStatus.DRAFT.value:
            raise bad_request("Only draft orders can be deleted")

        order.is_deleted = True
        order.updated_at = now
        self._append_history(
            order=order,
            actor_id=order.applicant_id,
            action="delete",
            from_status=order.status,
            to_status=order.status,
        )
        self.db.commit()

    def apply_action(self, order_id: int, payload: OrderActionRequest) -> Order:
        now = _now()
        order = self._get_order_model(order_id)
        current_status = OrderStatus(order.status)
        actor_id = payload.actor_id or order.applicant_id

        if current_status in FINAL_STATUSES:
            raise bad_request(f"Order is already {current_status.value} and cannot be changed")

        allowed_statuses, to_status, _message = TRANSITIONS[payload.action]
        if current_status not in allowed_statuses:
            raise bad_request(f"Cannot run {payload.action.value} from {current_status.value}")

        from_status = order.status

        if payload.action in {OrderAction.SUBMIT, OrderAction.CANCEL}:
            require_role(actor_id, {"site_user"})
            if actor_id != order.applicant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the applicant can submit or cancel this order",
                )

        elif payload.action in {OrderAction.APPROVE, OrderAction.RETURN, OrderAction.REJECT}:
            actor = require_role(actor_id, {"lab_manager"})
            lab_ids = set(actor.get("labIds", []))
            target_items = [
                item
                for item in order.items
                if item.lab_id in lab_ids
                and (payload.order_item_id is None or item.id == payload.order_item_id)
                and (
                    item.status == OrderStatus.PENDING_APPROVAL.value
                    or (order.status == OrderStatus.PENDING_APPROVAL.value and item.status == OrderStatus.DRAFT.value)
                )
            ]

            if not target_items:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No approvable order items for this manager",
                )

            for item in target_items:
                if item.status == OrderStatus.DRAFT.value:
                    item.status = OrderStatus.PENDING_APPROVAL.value

            if payload.action == OrderAction.APPROVE:
                exceeded_items = [item for item in target_items if item.quota_exceeded and not item.quota_override]
                if exceeded_items and not payload.quota_override:
                    raise bad_request("One or more order items exceed quota. Approve those items with quotaOverride and reason.")

                for item in target_items:
                    item.status = OrderStatus.APPROVED.value
                    item.approved_by = actor_id
                    item.approved_at = now
                    item.return_reason = None
                    item.reject_reason = None
                    if payload.quota_override:
                        item.quota_exceeded = True
                        item.quota_override = True
                        item.quota_override_reason = payload.reason
                        item.quota_approved_by = actor_id
                        item.quota_approved_at = now
                    item.updated_at = now

                order.status = self.aggregate_approval_status(order)
                if order.status == OrderStatus.APPROVED.value:
                    self.record_quota_usage(order)

            elif payload.action == OrderAction.RETURN:
                for item in target_items:
                    item.status = OrderStatus.RETURNED.value
                    item.return_reason = payload.reason
                    item.updated_at = now
                order.status = self.aggregate_approval_status(order)

            elif payload.action == OrderAction.REJECT:
                # If a manager rejects an item, the business rule is to reject the whole order.
                # Keep the existing authorization check (target_items must be non-empty for this manager)
                for item in order.items:
                    item.status = OrderStatus.REJECTED.value
                    item.reject_reason = payload.reason
                    item.updated_at = now
                order.status = OrderStatus.REJECTED.value

        else:
            if payload.action == OrderAction.CONFIRM_DELIVERY:
                require_role(actor_id, {"site_user"})
                if actor_id != order.applicant_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only the applicant can confirm sample delivery",
                    )
            else:
                require_role(actor_id, {"lab_staff", "lab_manager"})
            order.status = to_status.value

        if payload.action == OrderAction.SUBMIT:
            remaining_quota = self.effective_remaining_quota(order)
            for index, item in enumerate(order.items):
                item.status = OrderStatus.PENDING_APPROVAL.value
                item.approved_by = None
                item.approved_at = None
                item.return_reason = None
                item.reject_reason = None
                item.quota_override = False
                item.quota_override_reason = None
                item.quota_approved_by = None
                item.quota_approved_at = None
                item.quota_exceeded = index >= remaining_quota
                item.updated_at = now

            quota_check = self.check_quota_for_order(order)
            if quota_check["needOverride"]:
                order.last_reason = "配額超額，需主管特批"
            else:
                order.last_reason = None
            order.status = OrderStatus.PENDING_APPROVAL.value

        elif payload.action == OrderAction.CANCEL:
            order.status = OrderStatus.CANCELLED.value
            order.last_reason = payload.reason

        elif payload.reason is not None:
            order.last_reason = payload.reason

        order.updated_at = now
        self._append_history(
            order=order,
            actor_id=actor_id,
            action=payload.action.value,
            from_status=from_status,
            to_status=order.status,
            reason=payload.reason,
            quota_override=payload.quota_override,
        )
        self.db.commit()
        return self.get_order(order.id)

    def get_history(self, order_id: int) -> list[OrderHistory]:
        order = self._get_order_model(order_id)
        stmt = (
            select(OrderHistoryModel)
            .where(OrderHistoryModel.order_id == order.id)
            .order_by(OrderHistoryModel.action_time.asc(), OrderHistoryModel.id.asc())
        )
        histories = self.db.execute(stmt).scalars().all()
        return [_history_to_schema(history) for history in histories]

    def list_quota_settings(self) -> list[QuotaSettingModel]:
        stmt = select(QuotaSettingModel).order_by(QuotaSettingModel.id.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create_quota_setting(self, payload: QuotaPayload) -> QuotaSettingModel:
        now = _now()
        quota = QuotaSettingModel(
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            monthly_limit=payload.monthly_limit,
            urgent_limit=payload.urgent_limit,
            critical_limit=payload.critical_limit,
            is_active=payload.is_active,
            created_at=now,
            updated_at=now,
        )
        self.db.add(quota)
        self.db.commit()
        self.db.refresh(quota)
        return quota

    def update_quota_setting(self, quota_id: int, payload: QuotaPatchPayload) -> QuotaSettingModel:
        quota = self.db.get(QuotaSettingModel, quota_id)
        if quota is None:
            raise not_found("Quota setting not found")
        if payload.monthly_limit is not None:
            quota.monthly_limit = payload.monthly_limit
        if payload.urgent_limit is not None:
            quota.urgent_limit = payload.urgent_limit
        if payload.critical_limit is not None:
            quota.critical_limit = payload.critical_limit
        if payload.is_active is not None:
            quota.is_active = payload.is_active
        quota.updated_at = _now()
        self.db.commit()
        self.db.refresh(quota)
        return quota

    def check_quota_for_order(self, order: OrderModel) -> dict[str, Any]:
        checks = [
            self._quota_check("user", order.applicant_id, order.total_items, order.priority),
            self._quota_check("department", order.department_id, order.total_items, order.priority),
        ]
        checks = [item for item in checks if item is not None]
        allowed = all(item["allowed"] for item in checks) if checks else True
        return {"allowed": allowed, "needOverride": not allowed, "checks": checks}

    def check_quota(self, applicant_id: str, department_id: str, item_count: int, priority: str = "normal") -> dict[str, Any]:
        checks = [
            self._quota_check("user", applicant_id, item_count, priority),
            self._quota_check("department", department_id, item_count, priority),
        ]
        checks = [item for item in checks if item is not None]
        allowed = all(item["allowed"] for item in checks) if checks else True
        return {"allowed": allowed, "needOverride": not allowed, "checks": checks}

    def effective_remaining_quota(self, order: OrderModel) -> int:
        remaining_values = [
            self._quota_remaining("user", order.applicant_id, order.priority),
            self._quota_remaining("department", order.department_id, order.priority),
        ]
        remaining_values = [value for value in remaining_values if value is not None]
        if not remaining_values:
            return order.total_items
        return max(min(remaining_values), 0)

    def aggregate_approval_status(self, order: OrderModel) -> str:
        # Prioritize rejected and returned states over pending/draft so that a single
        # returned or rejected item updates the main order status accordingly.
        item_statuses = {item.status for item in order.items}
        if OrderStatus.REJECTED.value in item_statuses:
            return OrderStatus.REJECTED.value
        if OrderStatus.RETURNED.value in item_statuses:
            return OrderStatus.RETURNED.value
        if item_statuses == {OrderStatus.APPROVED.value}:
            return OrderStatus.APPROVED.value
        if OrderStatus.PENDING_APPROVAL.value in item_statuses or OrderStatus.DRAFT.value in item_statuses:
            return OrderStatus.PENDING_APPROVAL.value
        return order.status

    def record_quota_usage(self, order: OrderModel) -> None:
        if self.db.execute(select(QuotaUsageModel).where(QuotaUsageModel.order_id == order.id)).scalar_one_or_none():
            return
        now = _now()
        for scope_type, scope_id in (("user", order.applicant_id), ("department", order.department_id)):
            self.db.add(
                QuotaUsageModel(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    year=now.year,
                    month=now.month,
                    used_count=order.total_items,
                    urgent_used_count=order.total_items if order.priority == PriorityLevel.URGENT.value else 0,
                    critical_used_count=order.total_items if order.priority == PriorityLevel.CRITICAL.value else 0,
                    order_id=order.id,
                    created_at=now,
                    updated_at=now,
                )
            )

    def _quota_check(self, scope_type: str, scope_id: str, item_count: int, priority: str) -> dict[str, Any] | None:
        quota = self.db.execute(
            select(QuotaSettingModel)
            .where(
                QuotaSettingModel.scope_type == scope_type,
                QuotaSettingModel.scope_id == scope_id,
                QuotaSettingModel.is_active.is_(True),
            )
            .order_by(QuotaSettingModel.updated_at.desc(), QuotaSettingModel.id.desc())
        ).scalars().first()
        if quota is None:
            return None
        now = _now()
        usages = self.db.execute(
            select(QuotaUsageModel).where(
                QuotaUsageModel.scope_type == scope_type,
                QuotaUsageModel.scope_id == scope_id,
                QuotaUsageModel.year == now.year,
                QuotaUsageModel.month == now.month,
            )
        ).scalars().all()
        used = sum(item.used_count for item in usages)
        urgent_used = sum(item.urgent_used_count for item in usages)
        critical_used = sum(item.critical_used_count for item in usages)
        urgent_requested = item_count if priority == PriorityLevel.URGENT.value else 0
        critical_requested = item_count if priority == PriorityLevel.CRITICAL.value else 0
        monthly_allowed = used + item_count <= quota.monthly_limit
        urgent_allowed = quota.urgent_limit is None or urgent_used + urgent_requested <= quota.urgent_limit
        critical_allowed = quota.critical_limit is None or critical_used + critical_requested <= quota.critical_limit
        return {
            "scopeType": scope_type,
            "scopeId": scope_id,
            "used": used,
            "limit": quota.monthly_limit,
            "urgentUsed": urgent_used,
            "urgentLimit": quota.urgent_limit,
            "criticalUsed": critical_used,
            "criticalLimit": quota.critical_limit,
            "requested": item_count,
            "allowed": monthly_allowed and urgent_allowed and critical_allowed,
            "needOverride": not (monthly_allowed and urgent_allowed and critical_allowed),
        }

    def _quota_remaining(self, scope_type: str, scope_id: str, priority: str) -> int | None:
        check = self._quota_check(scope_type, scope_id, 0, priority)
        if check is None:
            return None

        remaining_values = [check["limit"] - check["used"]]
        if priority == PriorityLevel.URGENT.value and check["urgentLimit"] is not None:
            remaining_values.append(check["urgentLimit"] - check["urgentUsed"])
        if priority == PriorityLevel.CRITICAL.value and check["criticalLimit"] is not None:
            remaining_values.append(check["criticalLimit"] - check["criticalUsed"])

        return min(remaining_values)

    def _get_order_model(self, order_id: int) -> OrderModel:
        stmt = (
            select(OrderModel)
            .options(joinedload(OrderModel.items))
            .where(OrderModel.id == order_id, OrderModel.is_deleted.is_(False))
        )
        order = self.db.execute(stmt).unique().scalar_one_or_none()
        if order is None:
            raise not_found("Order not found")
        return order

    def _make_item(self, payload: OrderItemCreate, now: datetime) -> OrderItemModel:
        return OrderItemModel(
            sample_id=payload.sample_id,
            lab_id=payload.lab_id,
            experiment_id=payload.experiment_id,
            status=OrderStatus.DRAFT.value,
            created_at=now,
            updated_at=now,
        )

    def _append_history(
        self,
        order: OrderModel,
        actor_id: str,
        action: str,
        from_status: str | None,
        to_status: str,
        reason: str | None = None,
        quota_override: bool = False,
    ) -> None:
        self.db.add(
            OrderHistoryModel(
                order=order,
                actor_id=actor_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                quota_override=quota_override,
                action_time=_now(),
            )
        )


def get_order_repo(db: Session = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)


app = FastAPI(title="LIMS Order Management API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'draft'"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS approved_by VARCHAR(50)"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS return_reason TEXT"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS reject_reason TEXT"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_exceeded BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_override BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_override_reason TEXT"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_approved_by VARCHAR(50)"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_approved_at TIMESTAMPTZ"))
        connection.execute(text("UPDATE order_items SET status = 'draft' WHERE status IS NULL"))
    with Session(engine) as db:
        if db.execute(select(QuotaSettingModel)).first() is None:
            now = _now()
            db.add_all(
                [
                    QuotaSettingModel(
                        scope_type="user",
                        scope_id="user001",
                        monthly_limit=10,
                        urgent_limit=3,
                        critical_limit=1,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    ),
                    QuotaSettingModel(
                        scope_type="department",
                        scope_id="D001",
                        monthly_limit=50,
                        urgent_limit=10,
                        critical_limit=3,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    ),
                ]
            )
            db.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "order-management"}


@app.get("/api/me")
def get_me() -> ApiResponse:
    return ApiResponse(
        data={
            "userId": "manager001",
            "name": "LAB001/LAB002 主管",
            "role": "lab_manager",
            "labIds": ["LAB001", "LAB002"],
        }
    )


@app.get("/api/master-data")
def get_master_data() -> ApiResponse:
    return ApiResponse(
        data={
            "departments": DEPARTMENTS,
            "labs": LABS,
            "experiments": EXPERIMENTS,
            "statuses": [{"value": item.value, "label": item.value} for item in OrderStatus],
            "priorities": [{"value": item.value, "label": item.value} for item in PriorityLevel],
        }
    )


@app.get("/api/labs")
def get_labs() -> ApiResponse:
    return ApiResponse(data=LABS)


@app.get("/api/departments")
def get_departments() -> ApiResponse:
    return ApiResponse(data=DEPARTMENTS)


@app.get("/api/experiments")
def get_experiments(lab_id: str | None = Query(default=None, alias="labId")) -> ApiResponse:
    experiments = EXPERIMENTS
    if lab_id:
        experiments = [item for item in experiments if item["labId"] == lab_id]
    return ApiResponse(data=experiments)


@app.get("/api/orders")
def list_orders(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    applicant_id: str | None = Query(default=None, alias="applicantId"),
    repo: OrderRepository = Depends(get_order_repo),
) -> dict[str, Any]:
    orders = repo.list_orders(status_filter=status_filter, applicant_id=applicant_id)
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


@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    order = repo.create_order(payload)
    return ApiResponse(
        data={
            "id": order.id,
            "orderNo": order.order_no,
            "status": order.status,
            "priority": order.priority,
            "message": "委託單已建立",
        }
    )


@app.get("/api/orders/applicant/{applicant_id}")
def list_orders_by_applicant(
    applicant_id: str,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    return ApiResponse(
        data=[
            order.model_dump(by_alias=True)
            for order in repo.list_orders(applicant_id=applicant_id)
        ]
    )


@app.get("/api/orders/{order_id}")
def get_order(
    order_id: int,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    order = repo.get_order(order_id)
    return ApiResponse(data=order.model_dump(by_alias=True))


@app.patch("/api/orders/{order_id}")
def update_order(
    order_id: int,
    payload: OrderUpdate,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    order = repo.update_order(order_id, payload)
    return ApiResponse(data=order.model_dump(by_alias=True), message="委託單已更新")


@app.delete("/api/orders/{order_id}")
def delete_order(
    order_id: int,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    repo.delete_order(order_id)
    return ApiResponse(data={"id": order_id}, message="委託單已刪除")


@app.post("/api/orders/{order_id}/actions")
def handle_order_action(
    order_id: int,
    payload: OrderActionRequest,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    order = repo.apply_action(order_id, payload)
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


@app.get("/api/orders/{order_id}/history")
def get_order_history(
    order_id: int,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    return ApiResponse(
        data=[item.model_dump(by_alias=True) for item in repo.get_history(order_id)]
    )


SAMPLES = [
    {
        "id": "S001",
        "sampleNo": "S001",
        "name": "樣品 A",
        "status": "available",
        "description": "委託單測試用樣品",
    },
    {
        "id": "S002",
        "sampleNo": "S002",
        "name": "樣品 B",
        "status": "available",
        "description": "委託單測試用樣品",
    },
    {
        "id": "S003",
        "sampleNo": "S003",
        "name": "樣品 C",
        "status": "reserved",
        "description": "委託單測試用樣品",
    },
]

QUOTA_SETTINGS: list[dict[str, Any]] = [
    {
        "id": 1,
        "scopeType": "user",
        "scopeId": "user001",
        "monthlyLimit": 10,
        "urgentLimit": 3,
        "criticalLimit": 1,
        "isActive": True,
    },
    {
        "id": 2,
        "scopeType": "department",
        "scopeId": "D001",
        "monthlyLimit": 50,
        "urgentLimit": 10,
        "criticalLimit": 3,
        "isActive": True,
    },
]

NEXT_QUOTA_ID = 3


def _order_items_for(order_id: int, repo: OrderRepository) -> list[OrderItem]:
    return repo.get_order(order_id).items


def _used_count(scope_type: str, scope_id: str, repo: OrderRepository) -> int:
    if scope_type == "user":
        return sum(
            order.total_items
            for order in repo.list_orders(applicant_id=scope_id)
            if order.status not in {OrderStatus.DRAFT, OrderStatus.CANCELLED, OrderStatus.REJECTED}
        )
    if scope_type == "department":
        return sum(
            order.total_items
            for order in repo.list_orders()
            if order.department_id == scope_id
            and order.status not in {OrderStatus.DRAFT, OrderStatus.CANCELLED, OrderStatus.REJECTED}
        )
    return 0


def quota_to_dict(quota: QuotaSettingModel, repo: OrderRepository) -> dict[str, Any]:
    check = repo.check_quota(
        applicant_id=quota.scope_id if quota.scope_type == "user" else "user001",
        department_id=quota.scope_id if quota.scope_type == "department" else "D001",
        item_count=0,
    )
    matching = next(
        (item for item in check["checks"] if item["scopeType"] == quota.scope_type and item["scopeId"] == quota.scope_id),
        None,
    )
    used = matching["used"] if matching else 0
    return {
        "id": quota.id,
        "scopeType": quota.scope_type,
        "scopeId": quota.scope_id,
        "monthlyLimit": quota.monthly_limit,
        "urgentLimit": quota.urgent_limit,
        "criticalLimit": quota.critical_limit,
        "isActive": quota.is_active,
        "usedCount": used,
        "remaining": max(quota.monthly_limit - used, 0),
    }


@app.get("/api/samples")
def list_samples() -> ApiResponse:
    return ApiResponse(data=SAMPLES)


@app.get("/api/samples/{sample_id}")
def get_sample(sample_id: str) -> ApiResponse:
    sample = next((item for item in SAMPLES if item["id"] == sample_id), None)
    if sample is None:
        raise not_found("Sample not found")
    return ApiResponse(data=sample)


@app.get("/api/orders/{order_id}/wips")
def get_order_wips(
    order_id: int,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    items = _order_items_for(order_id, repo)
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
                "updatedAt": _now(),
            }
            for index, item in enumerate(items)
        ]
    )


@app.get("/api/wips")
def list_wips(
    order_id: int | None = Query(default=None, alias="orderId"),
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    if order_id is not None:
        return get_order_wips(order_id, repo)

    data: list[dict[str, Any]] = []
    for order in repo.list_orders():
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


@app.get("/api/orders/{order_id}/reports")
def get_order_reports(
    order_id: int,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    order = repo.get_order(order_id)
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


@app.get("/api/reports")
def list_reports(
    order_id: int | None = Query(default=None, alias="orderId"),
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    if order_id is not None:
        return get_order_reports(order_id, repo)
    data: list[dict[str, Any]] = []
    for order in repo.list_orders():
        data.extend(get_order_reports(order.id, repo).data)
    return ApiResponse(data=data)


@app.get("/api/orders/{order_id}/issues")
def get_order_issues(
    order_id: int,
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    order = repo.get_order(order_id)
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


@app.get("/api/issues")
def list_issues(
    order_id: int | None = Query(default=None, alias="orderId"),
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    if order_id is not None:
        return get_order_issues(order_id, repo)
    data: list[dict[str, Any]] = []
    for order in repo.list_orders():
        data.extend(get_order_issues(order.id, repo).data)
    return ApiResponse(data=data)


@app.get("/api/quotas")
def list_quotas(repo: OrderRepository = Depends(get_order_repo)) -> ApiResponse:
    return ApiResponse(data=[quota_to_dict(quota, repo) for quota in repo.list_quota_settings()])


@app.post("/api/quotas", status_code=status.HTTP_201_CREATED)
def create_quota(payload: QuotaPayload, repo: OrderRepository = Depends(get_order_repo)) -> ApiResponse:
    require_role(payload.actor_id, {"admin"})
    quota = repo.create_quota_setting(payload)
    return ApiResponse(data=quota_to_dict(quota, repo), message="配額設定已建立")


@app.patch("/api/quotas/{quota_id}")
def update_quota(quota_id: int, payload: QuotaPatchPayload, repo: OrderRepository = Depends(get_order_repo)) -> ApiResponse:
    require_role(payload.actor_id, {"admin"})
    quota = repo.update_quota_setting(quota_id, payload)
    return ApiResponse(data=quota_to_dict(quota, repo), message="配額設定已更新")


@app.get("/api/quotas/check")
def check_quota(
    applicant_id: str = Query(alias="applicantId"),
    department_id: str = Query(alias="departmentId"),
    item_count: int = Query(default=1, ge=1, alias="itemCount"),
    priority: PriorityLevel = Query(default=PriorityLevel.NORMAL),
    repo: OrderRepository = Depends(get_order_repo),
) -> ApiResponse:
    return ApiResponse(data=repo.check_quota(applicant_id, department_id, item_count, priority.value))
