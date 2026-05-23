from __future__ import annotations

from app.db.models.order_management import OrderHistoryModel, OrderItemModel, OrderModel
from app.core.order_enums import OrderStatus, PriorityLevel
from app.schemas.order import Order, OrderHistory, OrderItem


def item_to_schema(item: OrderItemModel) -> OrderItem:
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


def order_to_schema(order: OrderModel) -> Order:
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
        items=[item_to_schema(item) for item in order.items],
    )


def history_to_schema(history: OrderHistoryModel) -> OrderHistory:
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
