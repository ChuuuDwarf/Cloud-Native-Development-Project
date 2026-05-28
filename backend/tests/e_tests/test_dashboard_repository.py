"""Unit tests for :class:`DashboardRepository`.

These exercise the per-widget queries against the seeded test DB. The seed
ships a baseline corpus (admin / director / supervisors / engineers / sample
WIPs / machines / issues — see ``backend/scripts/seed_dev.py``), so most
tests assert non-negative invariants and scoping behavior rather than exact
counts, which would otherwise couple the test to seed churn.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.common.enums import ReportStatus
from app.common.enums.order_status import OrderStatus
from app.common.enums.role_d_zh import REPORT_ZH
from app.db.models.order_management import OrderItemModel, OrderModel
from app.db.models.reports import Report
from app.db.models.wips import Wip
from app.modules.dashboard.repository import DashboardRepository

pytestmark = pytest.mark.asyncio


# ----------------------------------------------------------------- KPI


async def test_kpi_new_orders_unscoped_returns_non_negative(db_session) -> None:
    repo = DashboardRepository(db_session)
    today, yday = await repo.kpi_new_orders(lab_codes=None)
    assert today >= 0
    assert yday >= 0


async def test_kpi_new_orders_scoped_is_subset_of_unscoped(db_session) -> None:
    repo = DashboardRepository(db_session)
    full_today, _ = await repo.kpi_new_orders(lab_codes=None)
    scoped_today, _ = await repo.kpi_new_orders(lab_codes=["LAB-A"])
    assert scoped_today <= full_today


async def test_kpi_new_orders_unknown_lab_returns_zero(db_session) -> None:
    repo = DashboardRepository(db_session)
    today, yday = await repo.kpi_new_orders(lab_codes=["LAB-DOES-NOT-EXIST"])
    assert today == 0
    assert yday == 0


async def test_kpi_completed_today_returns_non_negative(db_session) -> None:
    repo = DashboardRepository(db_session)
    today, yday = await repo.kpi_completed_today(lab_codes=None)
    assert today >= 0
    assert yday >= 0


async def test_kpi_returned_today_returns_non_negative(db_session) -> None:
    repo = DashboardRepository(db_session)
    today, yday = await repo.kpi_returned_today(lab_codes=None)
    assert today >= 0
    assert yday >= 0


async def test_kpi_pending_approval_scoped_le_unscoped(db_session) -> None:
    repo = DashboardRepository(db_session)
    full = await repo.kpi_pending_approval(lab_codes=None)
    scoped = await repo.kpi_pending_approval(lab_codes=["LAB-A"])
    assert scoped <= full


async def test_kpi_open_high_critical_issues_scoped_le_unscoped(db_session) -> None:
    repo = DashboardRepository(db_session)
    full = await repo.kpi_open_high_critical_issues(lab_codes=None)
    scoped = await repo.kpi_open_high_critical_issues(lab_codes=["LAB-A"])
    assert scoped <= full


# ----------------------------------------------------------- Machines


async def test_machines_unscoped_returns_list_of_tuples(db_session) -> None:
    repo = DashboardRepository(db_session)
    rows = await repo.machines(lab_codes=None)
    assert isinstance(rows, list)
    # Schema is 8-tuple per machine row.
    for r in rows:
        assert len(r) == 8


async def test_machines_status_translated_to_english(db_session) -> None:
    """DB stores Chinese statuses; repo must translate to canonical English."""
    repo = DashboardRepository(db_session)
    rows = await repo.machines(lab_codes=None)
    chinese_statuses = {"閒置", "使用中", "保養中", "故障中", "停用"}
    # No row should leak a raw Chinese status; either translated or already EN.
    for r in rows:
        assert r[3] not in chinese_statuses


async def test_machines_scoped_subset(db_session) -> None:
    repo = DashboardRepository(db_session)
    full = await repo.machines(lab_codes=None)
    scoped = await repo.machines(lab_codes=["LAB-A"])
    assert len(scoped) <= len(full)
    # All scoped rows must belong to LAB-A.
    for r in scoped:
        assert r[2] == "LAB-A"


# ----------------------------------------------------------- WIP pipeline


async def test_wip_pipeline_returns_six_buckets(db_session) -> None:
    repo = DashboardRepository(db_session)
    counts = await repo.wip_pipeline_counts(lab_codes=None)
    assert set(counts.keys()) == {
        "waiting_dispatch",
        "dispatched",
        "in_progress",
        "awaiting_handoff",
        "done",
        "terminated",
    }
    for now, prev in counts.values():
        assert now >= 0
        assert prev >= 0


async def test_wip_pipeline_unknown_lab_all_zero(db_session) -> None:
    repo = DashboardRepository(db_session)
    counts = await repo.wip_pipeline_counts(lab_codes=["LAB-DOES-NOT-EXIST"])
    assert all(n == 0 and p == 0 for (n, p) in counts.values())


# ----------------------------------------------------------------- Triage


async def test_triage_pending_approvals_limit_respected(db_session) -> None:
    repo = DashboardRepository(db_session)
    rows = await repo.triage_pending_approvals(lab_codes=None, limit=3)
    assert len(rows) <= 3


async def test_triage_pending_approvals_ordered_oldest_first(db_session) -> None:
    repo = DashboardRepository(db_session)
    rows = await repo.triage_pending_approvals(lab_codes=None, limit=20)
    ts = [r[2] for r in rows]
    assert ts == sorted(ts)


async def test_triage_unack_issues_limit_respected(db_session) -> None:
    """We don't have a known user_id seed, but pass an arbitrary UUID — the
    query should still execute and return high/critical open issues.
    """
    import uuid

    repo = DashboardRepository(db_session)
    rows = await repo.triage_unack_issues(lab_codes=None, user_id=uuid.uuid4(), limit=5)
    assert len(rows) <= 5


# ----------------------------------------------------------- Escalations


async def test_recent_escalations_limit_respected(db_session) -> None:
    repo = DashboardRepository(db_session)
    rows = await repo.recent_escalations(lab_codes=None, limit=5)
    assert len(rows) <= 5
    # Each row is 6-tuple per schema.
    for r in rows:
        assert len(r) == 6


# ------------------------------------------------------------ Completions


async def test_recent_completions_limit_respected(db_session) -> None:
    repo = DashboardRepository(db_session)
    rows = await repo.recent_completions(lab_codes=None, limit=5)
    assert len(rows) <= 5


# ------------------------------------------------------------ Leaderboard


async def test_lab_leaderboard_sorted_by_completed_desc(db_session) -> None:
    repo = DashboardRepository(db_session)
    rows = await repo.lab_leaderboard(limit=10)
    completed_values = [r[1] for r in rows]
    assert completed_values == sorted(completed_values, reverse=True)


async def test_lab_leaderboard_contains_seeded_labs(db_session) -> None:
    """Seed defines LAB-A/B/C. They should all appear (even at zero counts)."""
    repo = DashboardRepository(db_session)
    rows = await repo.lab_leaderboard(limit=10)
    lab_names = {r[0] for r in rows}
    # Seed lab display names — these are stable identities.
    assert "材料分析實驗室" in lab_names
    assert "電性測試實驗室" in lab_names
    assert "可靠度實驗室" in lab_names


# ------------------------------------------------------- regression: B1
#
# B1: Order lab-scoping must walk OrderItemModel.lab_id, NOT Wip.lab_name.
# Pending-approval orders have no WIPs yet, so a Wip-join would under-count
# them to zero in a lab_supervisor's view.


async def test_pending_approval_order_scoped_via_items_no_wips(db_session) -> None:
    """An order at PENDING_APPROVAL with an OrderItem in LAB-A and NO Wip rows
    must still appear in the LAB-A supervisor's KPI + triage list."""
    now = datetime.now(UTC)
    order = OrderModel(
        order_no=f"REG-B1-{uuid.uuid4().hex[:8]}",
        applicant_id="reg-applicant",
        department_id="DEPT-RD",
        apply_date=now,
        status=OrderStatus.PENDING_APPROVAL.value,
        priority="normal",
        total_items=1,
    )
    db_session.add(order)
    await db_session.flush()
    db_session.add(
        OrderItemModel(
            order_id=order.id,
            sample_id="SMP-B1",
            sample_name="B1 sample",
            lab_id="LAB-A",
            experiment_id="EXP-B1",
            status=OrderStatus.PENDING_APPROVAL.value,
        )
    )
    await db_session.commit()

    repo = DashboardRepository(db_session)
    pending = await repo.kpi_pending_approval(lab_codes=["LAB-A"])
    assert pending >= 1, "lab_supervisor in LAB-A should see the pending-approval order"

    triage = await repo.triage_pending_approvals(lab_codes=["LAB-A"], limit=20)
    order_nos = [r[0] for r in triage]
    assert order.order_no in order_nos


# ------------------------------------------------------- regression: B2
#
# B2: A completed WIP with TWO RETURNED reports must count exactly ONCE in
# wip_pipeline_counts. The original JOIN-and-count over-counted.


async def test_completed_wip_with_multiple_reports_counted_once(db_session) -> None:
    """Seed 1 completed Wip + 2 RETURNED Reports referencing the same wip_no.
    The wip must contribute exactly +1 to the pipeline bucket and the
    repository's invariant ``total = sum(stages)`` must continue to hold.
    """
    order_no = f"REG-B2-{uuid.uuid4().hex[:8]}"
    wip_no = f"WIP-B2-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC)

    # Order in a non-pickup status → WIP lands in awaiting_handoff bucket.
    db_session.add(
        OrderModel(
            order_no=order_no,
            applicant_id="reg-applicant",
            department_id="DEPT-RD",
            apply_date=now,
            status=OrderStatus.IN_PROGRESS.value,
            priority="normal",
            total_items=1,
        )
    )

    # Wip is naive TIMESTAMP — use naive datetimes for its time columns.
    naive_now = now.replace(tzinfo=None)
    db_session.add(
        Wip(
            wip_no=wip_no,
            sample_id=uuid.uuid4(),
            order_no=order_no,
            lab_name="材料分析實驗室",
            experiment_item="reg",
            priority="normal",
            status="completed",
            progress=100,
            completed_at=naive_now,
        )
    )
    await db_session.flush()

    returned_zh = REPORT_ZH[ReportStatus.RETURNED]
    db_session.add_all(
        [
            Report(
                report_id=f"RPT-B2-{uuid.uuid4().hex[:8]}",
                order_id=order_no,
                wip_id=wip_no,
                title="r1",
                status=returned_zh,
                created_by="reg",
            ),
            Report(
                report_id=f"RPT-B2-{uuid.uuid4().hex[:8]}",
                order_id=order_no,
                wip_id=wip_no,
                title="r2",
                status=returned_zh,
                created_by="reg",
            ),
        ]
    )
    await db_session.commit()

    repo = DashboardRepository(db_session)
    counts = await repo.wip_pipeline_counts(lab_codes=None)

    total = sum(c[0] for c in counts.values())
    # Pipeline buckets are mutually exclusive by status × order-status, so the
    # total must equal the count of DISTINCT WIPs in the documented statuses.
    # If the JOIN-and-count regression returns (a JOIN against Report would
    # multi-count completed WIPs with >1 RETURNED report) this assertion
    # catches it.
    distinct_wip_count_stmt = select(Wip.wip_no).where(
        Wip.status.in_(
            (
                "waiting_schedule",
                "scheduled",
                "dispatched",
                "running",
                "paused",
                "completed",
                "terminated",
            )
        )
    )
    distinct_wip_count = len((await db_session.execute(distinct_wip_count_stmt)).all())
    assert total <= distinct_wip_count, (
        f"pipeline total ({total}) exceeds distinct wip count ({distinct_wip_count}) — "
        "multi-report join is double-counting"
    )
    # And the multi-report wip itself contributes >=1 to awaiting_handoff.
    assert counts["awaiting_handoff"][0] >= 1


# ------------------------------------------------------- regression: B3
#
# B3: WIPs in every CHECK-allowed status must land in the documented bucket.
# The previous in_progress constant referenced WipStatus.UNLOADED /
# WAITING_CONFIRM which are NOT in the DB CHECK vocabulary, and ``paused``
# (which IS allowed) was silently dropped from every bucket.


async def test_all_valid_wip_statuses_land_in_correct_bucket(db_session) -> None:
    """Seed Wips with each DB-CHECK status and verify bucket allocation."""
    now = datetime.now(UTC)
    naive_now = now.replace(tzinfo=None)
    lab = "材料分析實驗室"
    suite_id = uuid.uuid4().hex[:8]
    order_pending_pickup_no = f"REG-B3a-{suite_id}"
    order_pickup_no = f"REG-B3b-{suite_id}"
    db_session.add_all(
        [
            OrderModel(
                order_no=order_pending_pickup_no,
                applicant_id="reg-applicant",
                department_id="DEPT-RD",
                apply_date=now,
                status=OrderStatus.IN_PROGRESS.value,
                priority="normal",
                total_items=1,
            ),
            OrderModel(
                order_no=order_pickup_no,
                applicant_id="reg-applicant",
                department_id="DEPT-RD",
                apply_date=now,
                status=OrderStatus.WAITING_PICKUP.value,
                priority="normal",
                total_items=1,
            ),
        ]
    )
    await db_session.flush()

    # Build one Wip per CHECK status. "completed" appears twice — one per
    # order status so it lands in awaiting_handoff vs done.
    seeded = [
        ("waiting_schedule", order_pending_pickup_no),
        ("scheduled", order_pending_pickup_no),
        ("dispatched", order_pending_pickup_no),
        ("running", order_pending_pickup_no),
        ("paused", order_pending_pickup_no),
        ("completed", order_pending_pickup_no),  # → awaiting_handoff (after report)
        ("completed", order_pickup_no),  # → done (after report)
        ("terminated", order_pending_pickup_no),
    ]
    wip_nos: list[str] = []
    for status, order_no in seeded:
        wip_no = f"WIP-B3-{status[:4]}-{uuid.uuid4().hex[:6]}"
        wip_nos.append(wip_no)
        db_session.add(
            Wip(
                wip_no=wip_no,
                sample_id=uuid.uuid4(),
                order_no=order_no,
                lab_name=lab,
                experiment_item="reg",
                priority="normal",
                status=status,
                progress=100 if status == "completed" else 0,
                completed_at=naive_now if status == "completed" else None,
            )
        )

    returned_zh = REPORT_ZH[ReportStatus.RETURNED]
    completed_indices = [i for i, (s, _) in enumerate(seeded) if s == "completed"]
    for idx in completed_indices:
        db_session.add(
            Report(
                report_id=f"RPT-B3-{uuid.uuid4().hex[:8]}",
                order_id=seeded[idx][1],
                wip_id=wip_nos[idx],
                title="r",
                status=returned_zh,
                created_by="reg",
            )
        )
    await db_session.commit()

    # Resolve which buckets the seed must contribute to. Each non-completed
    # status seeds exactly +1; "completed" with a RETURNED report and a
    # non-pickup order → awaiting_handoff; "completed" + pickup → done.
    repo = DashboardRepository(db_session)
    counts = await repo.wip_pipeline_counts(lab_codes=None)
    # The "waiting_schedule" seed has no dispatch row → waiting_dispatch.
    assert counts["waiting_dispatch"][0] >= 1
    # scheduled + dispatched land here.
    assert counts["dispatched"][0] >= 2
    # running + paused must both count — paused was missing from the
    # original _WIP_IN_PROGRESS_STATES constant.
    assert counts["in_progress"][0] >= 2
    assert counts["awaiting_handoff"][0] >= 1
    assert counts["done"][0] >= 1
    assert counts["terminated"][0] >= 1
