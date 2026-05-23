from __future__ import annotations

from app.core.order_enums import OrderAction, OrderStatus

MAX_ITEMS_PER_ORDER = 10

TRANSITIONS: dict[OrderAction, tuple[set[OrderStatus], OrderStatus, str]] = {
    OrderAction.SUBMIT: (
        {OrderStatus.DRAFT, OrderStatus.RETURNED},
        OrderStatus.PENDING_APPROVAL,
        "委託單已送出簽核",
    ),
    OrderAction.CANCEL: (
        {OrderStatus.DRAFT, OrderStatus.RETURNED, OrderStatus.PENDING_APPROVAL},
        OrderStatus.CANCELLED,
        "委託單已取消",
    ),
    OrderAction.APPROVE: (
        {OrderStatus.PENDING_APPROVAL},
        OrderStatus.APPROVED,
        "委託單已核准",
    ),
    OrderAction.RETURN: (
        {OrderStatus.PENDING_APPROVAL},
        OrderStatus.RETURNED,
        "委託單已退回補件",
    ),
    OrderAction.REJECT: (
        {OrderStatus.PENDING_APPROVAL},
        OrderStatus.REJECTED,
        "委託單已拒絕",
    ),
    OrderAction.CONFIRM_DELIVERY: (
        {OrderStatus.APPROVED},
        OrderStatus.SAMPLE_DELIVERED,
        "已確認送樣",
    ),
    OrderAction.CONFIRM_RECEIVED: (
        {OrderStatus.SAMPLE_DELIVERED},
        OrderStatus.SAMPLE_RECEIVED,
        "已確認收樣",
    ),
    OrderAction.READY_FOR_PICKUP: (
        {OrderStatus.SAMPLE_RECEIVED},
        OrderStatus.READY_FOR_PICKUP,
        "已標記待取件",
    ),
    OrderAction.CLOSE: (
        {OrderStatus.READY_FOR_PICKUP},
        OrderStatus.CLOSED,
        "委託單已結案",
    ),
}

FINAL_STATUSES = {OrderStatus.CLOSED, OrderStatus.REJECTED, OrderStatus.CANCELLED}
EDITABLE_STATUSES = {OrderStatus.DRAFT, OrderStatus.RETURNED}
