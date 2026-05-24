from enum import StrEnum


class OrderStatus(StrEnum):
    """Order lifecycle states (docs/flow.md)."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    RETURNED = "returned"
    REJECTED = "rejected"
    APPROVED = "approved"
    WAITING_SAMPLE = "waiting_sample"
    RECEIVED = "received"
    SPLIT = "split"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    WAITING_RESULT_CONFIRM = "waiting_result_confirm"
    COMPLETED = "completed"
    WAITING_REPORT_RETURN = "waiting_report_return"
    WAITING_PICKUP = "waiting_pickup"
    CLOSED = "closed"
    CANCELLED = "cancelled"
