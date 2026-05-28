"""Unit tests for :class:`DashboardRepository`.

These exercise the per-widget queries against the seeded test DB. The seed
ships a baseline corpus (admin / director / supervisors / engineers / sample
WIPs / machines / issues — see ``backend/scripts/seed_dev.py``), so most
tests assert non-negative invariants and scoping behavior rather than exact
counts, which would otherwise couple the test to seed churn.
"""

from __future__ import annotations

import pytest

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
