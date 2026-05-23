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
