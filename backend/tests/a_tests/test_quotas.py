"""Tests for the quota subsystem (組員 A): /api/quotas routes + OrderRepository
quota arithmetic.

The quota route surface (list / create / patch / check) was previously
untested. We drive the API for the route + service + serializer paths, then
exercise the branchy repo internals (``_quota_check``, ``_reserved_quota_count``,
``effective_remaining_quota``, ``aggregate_approval_status``) directly against
the test DB for the per-branch arithmetic that the API doesn't easily reach
(urgent/critical sub-limits, reserved-count from PENDING_APPROVAL orders).

Scope-ids are uniquified per test so the seeded corpus and parallel tests can't
collide (the seed DB persists across the session).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.common.enums import OrderStatus
from app.core.order_enums import PriorityLevel
from app.db.models.order_management import OrderModel, QuotaSettingModel, QuotaUsageModel
from app.repos.order_repo import OrderRepository

pytestmark = pytest.mark.asyncio


def _suite() -> str:
    return uuid.uuid4().hex[:8]


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Route-level: /api/quotas
# ---------------------------------------------------------------------------


async def test_list_quotas_returns_envelope(admin_client: AsyncClient) -> None:
    """GET /api/quotas returns the ApiResponse envelope with a data list.

    Note: this list endpoint is intentionally not auth-gated in the router
    (no get_current_user dependency), unlike create/patch which require admin.
    """
    resp = await admin_client.get("/api/quotas")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


async def test_admin_can_create_and_list_quota(admin_client: AsyncClient) -> None:
    suite = _suite()
    scope_id = f"DEPT-Q-{suite}"
    resp = await admin_client.post(
        "/api/quotas",
        json={
            "scopeType": "department",
            "scopeId": scope_id,
            "monthlyLimit": 50,
            "urgentLimit": 5,
            "criticalLimit": 2,
            "isActive": True,
        },
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()["data"]
    assert created["scopeId"] == scope_id
    assert created["monthlyLimit"] == 50
    # Fresh quota with no usage → fully remaining.
    assert created["usedCount"] == 0
    assert created["remaining"] == 50

    listed = (await admin_client.get("/api/quotas")).json()["data"]
    assert any(q["scopeId"] == scope_id for q in listed)


async def test_admin_can_patch_quota(admin_client: AsyncClient) -> None:
    suite = _suite()
    scope_id = f"DEPT-QP-{suite}"
    quota_id = (
        await admin_client.post(
            "/api/quotas",
            json={"scopeType": "department", "scopeId": scope_id, "monthlyLimit": 10},
        )
    ).json()["data"]["id"]

    patched = (
        await admin_client.patch(f"/api/quotas/{quota_id}", json={"monthlyLimit": 99})
    ).json()["data"]
    assert patched["monthlyLimit"] == 99


async def test_patch_unknown_quota_is_404(admin_client: AsyncClient) -> None:
    resp = await admin_client.patch("/api/quotas/99999999", json={"monthlyLimit": 1})
    assert resp.status_code == 404


async def test_non_admin_cannot_create_quota(plant_user_client: AsyncClient) -> None:
    resp = await plant_user_client.post(
        "/api/quotas",
        json={"scopeType": "department", "scopeId": "DEPT-X", "monthlyLimit": 1},
    )
    assert resp.status_code == 403


async def test_check_quota_route_reports_allowed_when_under_limit(
    admin_client: AsyncClient,
) -> None:
    suite = _suite()
    dept = f"DEPT-CHK-{suite}"
    await admin_client.post(
        "/api/quotas",
        json={"scopeType": "department", "scopeId": dept, "monthlyLimit": 100},
    )
    resp = await admin_client.get(
        "/api/quotas/check",
        params={"departmentId": dept, "itemCount": 3},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["allowed"] is True
    assert data["needOverride"] is False
    dept_check = next(c for c in data["checks"] if c["scopeId"] == dept)
    assert dept_check["limit"] == 100


async def test_check_quota_route_blocks_when_over_limit(admin_client: AsyncClient) -> None:
    suite = _suite()
    dept = f"DEPT-OVER-{suite}"
    await admin_client.post(
        "/api/quotas",
        json={"scopeType": "department", "scopeId": dept, "monthlyLimit": 2},
    )
    resp = await admin_client.get(
        "/api/quotas/check",
        params={"departmentId": dept, "itemCount": 5},
    )
    data = resp.json()["data"]
    assert data["allowed"] is False
    assert data["needOverride"] is True


async def test_check_quota_route_no_setting_is_allowed(admin_client: AsyncClient) -> None:
    """No quota setting for the scope → unconstrained (allowed, no checks)."""
    resp = await admin_client.get(
        "/api/quotas/check",
        params={"departmentId": f"DEPT-NONE-{_suite()}", "itemCount": 999},
    )
    data = resp.json()["data"]
    assert data["allowed"] is True
    assert data["checks"] == []


# ---------------------------------------------------------------------------
# Repository arithmetic: _quota_check
# ---------------------------------------------------------------------------


async def _seed_quota(
    db_session,
    *,
    scope_type: str,
    scope_id: str,
    monthly_limit: int,
    urgent_limit: int | None = None,
    critical_limit: int | None = None,
    is_active: bool = True,
) -> QuotaSettingModel:
    now = _now()
    q = QuotaSettingModel(
        scope_type=scope_type,
        scope_id=scope_id,
        monthly_limit=monthly_limit,
        urgent_limit=urgent_limit,
        critical_limit=critical_limit,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db_session.add(q)
    await db_session.flush()
    return q


async def _seed_usage(
    db_session,
    *,
    scope_type: str,
    scope_id: str,
    used: int = 0,
    urgent: int = 0,
    critical: int = 0,
) -> None:
    now = _now()
    db_session.add(
        QuotaUsageModel(
            scope_type=scope_type,
            scope_id=scope_id,
            year=now.year,
            month=now.month,
            used_count=used,
            urgent_used_count=urgent,
            critical_used_count=critical,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()


async def test_quota_check_inactive_setting_is_ignored(db_session) -> None:
    suite = _suite()
    scope_id = f"user-inactive-{suite}"
    await _seed_quota(
        db_session, scope_type="user", scope_id=scope_id, monthly_limit=1, is_active=False
    )
    await db_session.commit()

    repo = OrderRepository(db_session)
    # Inactive setting → no constraint found → None.
    assert await repo._quota_check("user", scope_id, item_count=5, priority="normal") is None


async def test_quota_check_counts_used_toward_limit(db_session) -> None:
    suite = _suite()
    scope_id = f"dept-used-{suite}"
    await _seed_quota(db_session, scope_type="department", scope_id=scope_id, monthly_limit=10)
    await _seed_usage(db_session, scope_type="department", scope_id=scope_id, used=8)
    await db_session.commit()

    repo = OrderRepository(db_session)
    check = await repo._quota_check("department", scope_id, item_count=2, priority="normal")
    assert check is not None
    assert check["used"] == 8
    assert check["remaining"] == 2  # 10 - 8
    assert check["allowed"] is True  # 8 + 2 == 10
    # One more item would exceed.
    over = await repo._quota_check("department", scope_id, item_count=3, priority="normal")
    assert over["allowed"] is False


async def test_quota_check_urgent_sublimit_blocks_even_when_monthly_ok(db_session) -> None:
    suite = _suite()
    scope_id = f"user-urgent-{suite}"
    await _seed_quota(
        db_session, scope_type="user", scope_id=scope_id, monthly_limit=100, urgent_limit=1
    )
    await _seed_usage(db_session, scope_type="user", scope_id=scope_id, used=0, urgent=1)
    await db_session.commit()

    repo = OrderRepository(db_session)
    # Monthly has tons of room, but urgent sub-limit (1) is already consumed.
    check = await repo._quota_check(
        "user", scope_id, item_count=1, priority=PriorityLevel.URGENT.value
    )
    assert check["allowed"] is False


async def test_quota_check_critical_sublimit_blocks(db_session) -> None:
    suite = _suite()
    scope_id = f"user-crit-{suite}"
    await _seed_quota(
        db_session, scope_type="user", scope_id=scope_id, monthly_limit=100, critical_limit=0
    )
    await db_session.commit()

    repo = OrderRepository(db_session)
    check = await repo._quota_check(
        "user", scope_id, item_count=1, priority=PriorityLevel.CRITICAL.value
    )
    assert check["allowed"] is False


# ---------------------------------------------------------------------------
# _reserved_quota_count — pending-approval orders count against quota.
# ---------------------------------------------------------------------------


async def test_reserved_quota_counts_pending_orders(db_session) -> None:
    suite = _suite()
    applicant = f"applicant-res-{suite}"
    # Two PENDING_APPROVAL orders (reserved) + one DRAFT (not reserved).
    for n, (status, items) in enumerate(
        [
            (OrderStatus.PENDING_APPROVAL.value, 3),
            (OrderStatus.PENDING_APPROVAL.value, 2),
            (OrderStatus.DRAFT.value, 9),
        ]
    ):
        db_session.add(
            OrderModel(
                order_no=f"Q-RES-{suite}-{n}",
                applicant_id=applicant,
                department_id="DEPT-RD",
                apply_date=_now(),
                status=status,
                priority="normal",
                total_items=items,
            )
        )
    await db_session.flush()
    await db_session.commit()

    repo = OrderRepository(db_session)
    # Only the two PENDING_APPROVAL orders count: 3 + 2 = 5.
    assert await repo._reserved_quota_count("user", applicant) == 5


async def test_reserved_quota_zero_for_sentinel_scope(db_session) -> None:
    repo = OrderRepository(db_session)
    assert await repo._reserved_quota_count("user", "__not_applicable__") == 0
    assert await repo._reserved_quota_count("user", "") == 0
    # Unknown scope_type → 0.
    assert await repo._reserved_quota_count("bogus", "something") == 0


async def test_quota_check_reserved_eats_into_remaining(db_session) -> None:
    """A pending order's items reduce the effective remaining quota for the
    same applicant, on top of recorded usage."""
    suite = _suite()
    applicant = f"applicant-eat-{suite}"
    await _seed_quota(db_session, scope_type="user", scope_id=applicant, monthly_limit=10)
    await _seed_usage(db_session, scope_type="user", scope_id=applicant, used=4)
    db_session.add(
        OrderModel(
            order_no=f"Q-EAT-{suite}",
            applicant_id=applicant,
            department_id="DEPT-RD",
            apply_date=_now(),
            status=OrderStatus.PENDING_APPROVAL.value,
            priority="normal",
            total_items=3,
        )
    )
    await db_session.commit()

    repo = OrderRepository(db_session)
    check = await repo._quota_check("user", applicant, item_count=1, priority="normal")
    # used(4) + reserved(3) = 7 effective; remaining = 10 - 7 = 3.
    assert check["used"] == 4
    assert check["reserved"] == 3
    assert check["effectiveUsed"] == 7
    assert check["remaining"] == 3


# ---------------------------------------------------------------------------
# effective_remaining_quota — min across user/department, floored at 0.
# ---------------------------------------------------------------------------


async def test_effective_remaining_quota_no_settings_returns_total_items(db_session) -> None:
    suite = _suite()
    order = OrderModel(
        order_no=f"Q-ERQ-NONE-{suite}",
        applicant_id=f"u-{suite}",
        department_id=f"d-{suite}",
        apply_date=_now(),
        status=OrderStatus.DRAFT.value,
        priority="normal",
        total_items=7,
    )
    repo = OrderRepository(db_session)
    # No quota settings for either scope → falls back to total_items.
    assert await repo.effective_remaining_quota(order) == 7


async def test_effective_remaining_quota_takes_tighter_scope(db_session) -> None:
    suite = _suite()
    applicant = f"u-tight-{suite}"
    dept = f"d-tight-{suite}"
    await _seed_quota(db_session, scope_type="user", scope_id=applicant, monthly_limit=4)
    await _seed_quota(db_session, scope_type="department", scope_id=dept, monthly_limit=20)
    await db_session.commit()

    order = OrderModel(
        order_no=f"Q-ERQ-{suite}",
        applicant_id=applicant,
        department_id=dept,
        apply_date=_now(),
        status=OrderStatus.DRAFT.value,
        priority="normal",
        total_items=99,
    )
    repo = OrderRepository(db_session)
    # min(user=4, dept=20) = 4.
    assert await repo.effective_remaining_quota(order) == 4


# ---------------------------------------------------------------------------
# aggregate_approval_status — pure rollup logic over item statuses.
# ---------------------------------------------------------------------------


class _Item:
    def __init__(self, status: str) -> None:
        self.status = status


class _Order:
    def __init__(self, items, status: str = "in_progress") -> None:
        self.items = items
        self.status = status


async def test_aggregate_status_rejected_wins(db_session) -> None:
    repo = OrderRepository(db_session)
    order = _Order(
        [
            _Item(OrderStatus.APPROVED.value),
            _Item(OrderStatus.REJECTED.value),
            _Item(OrderStatus.PENDING_APPROVAL.value),
        ]
    )
    assert repo.aggregate_approval_status(order) == OrderStatus.REJECTED.value


async def test_aggregate_status_returned_over_pending(db_session) -> None:
    repo = OrderRepository(db_session)
    order = _Order([_Item(OrderStatus.RETURNED.value), _Item(OrderStatus.PENDING_APPROVAL.value)])
    assert repo.aggregate_approval_status(order) == OrderStatus.RETURNED.value


async def test_aggregate_status_all_approved(db_session) -> None:
    repo = OrderRepository(db_session)
    order = _Order([_Item(OrderStatus.APPROVED.value), _Item(OrderStatus.APPROVED.value)])
    assert repo.aggregate_approval_status(order) == OrderStatus.APPROVED.value


async def test_aggregate_status_pending_when_mixed_pending_draft(db_session) -> None:
    repo = OrderRepository(db_session)
    order = _Order([_Item(OrderStatus.PENDING_APPROVAL.value), _Item(OrderStatus.DRAFT.value)])
    assert repo.aggregate_approval_status(order) == OrderStatus.PENDING_APPROVAL.value


async def test_aggregate_status_falls_back_to_order_status(db_session) -> None:
    repo = OrderRepository(db_session)
    # No actionable item statuses → keep the order's own status.
    order = _Order([_Item(OrderStatus.COMPLETED.value)], status="in_progress")
    assert repo.aggregate_approval_status(order) == "in_progress"
