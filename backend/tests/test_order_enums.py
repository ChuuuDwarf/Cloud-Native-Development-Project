"""Guards the cross-module order-enum regression.

A's order serializer (``app/repos/order_mappers.py``) parses ``orders.status`` /
``orders.priority`` through ``app.core.order_enums``. It used to 500
(``ValueError``) whenever C/D wrote a status A didn't know (``waiting_pickup``,
``scheduled`` …) or a ``high`` priority into the shared ``orders`` table. The
enums are now supersets; these tests pin that so the list endpoint can't regress.
"""

import pytest

from app.core.order_enums import OrderStatus, PriorityLevel

# Canonical lifecycle values written by C (排程) and D (執行/結案).
CROSS_MODULE_STATUSES = [
    "waiting_sample",
    "received",
    "split",
    "scheduled",
    "in_progress",
    "waiting_result_confirm",
    "completed",
    "waiting_report_return",
    "waiting_pickup",
]

# A's own lifecycle values must keep working too.
A_NATIVE_STATUSES = [
    "draft",
    "pending_approval",
    "approved",
    "returned",
    "rejected",
    "cancelled",
    "sample_delivered",
    "sample_received",
    "ready_for_pickup",
    "closed",
]


@pytest.mark.parametrize("value", CROSS_MODULE_STATUSES + A_NATIVE_STATUSES)
def test_order_status_parses_without_valueerror(value: str) -> None:
    assert OrderStatus(value).value == value


@pytest.mark.parametrize("value", ["normal", "urgent", "critical", "low", "medium", "high"])
def test_priority_level_parses_without_valueerror(value: str) -> None:
    assert PriorityLevel(value).value == value
