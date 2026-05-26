from __future__ import annotations

from enum import StrEnum


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
    # Cross-module lifecycle values written into the shared ``orders`` table by
    # C (排程/dispatch) and D (結案), using the canonical vocabulary in
    # ``app.common.enums.OrderStatus``. Listed here so A's serializer can parse
    # them instead of raising ``ValueError`` (the frontend already labels these).
    WAITING_SAMPLE = "waiting_sample"
    RECEIVED = "received"
    SPLIT = "split"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    WAITING_RESULT_CONFIRM = "waiting_result_confirm"
    COMPLETED = "completed"
    WAITING_REPORT_RETURN = "waiting_report_return"
    WAITING_PICKUP = "waiting_pickup"


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
    # low/medium/high scale written by other modules' order creation; accepted
    # here so A's serializer can parse them instead of raising ValueError.
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
