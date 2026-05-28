"""Service-level tests for :class:`DashboardService`.

We construct :class:`CurrentUser` directly from the seeded users so the
tests exercise role-aware scoping (cross-lab vs single-lab) without going
through the HTTP / JWT layer.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.dependencies import CurrentUser
from app.db.models import User
from app.db.models.roles import Role
from app.modules.dashboard.service import DashboardService
from app.services.auth import project_user

pytestmark = pytest.mark.asyncio


async def _user_by_email(db_session, email: str) -> CurrentUser:
    """Build a CurrentUser for the seeded ``email`` — same projection the
    real auth dependency uses, so role + permissions match production."""
    stmt = (
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )
    user = (await db_session.execute(stmt)).scalar_one()
    role, perms = project_user(user)
    return CurrentUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=role,
        permissions=perms,
        lab_id=user.lab_id,
        lab_code=user.lab.code if user.lab else None,
        department_id=user.department_id,
    )


# --------------------------------------------------------------- general_supervisor


async def test_general_supervisor_sees_leaderboard_and_no_completions(
    db_session,
) -> None:
    user = await _user_by_email(db_session, "director@example.com")
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)

    assert snap.viewer_role == "general_supervisor"
    assert snap.viewer_lab is None
    assert snap.lab_leaderboard is not None
    assert snap.recent_completions is None


async def test_general_supervisor_kpi_bar_has_all_five_cards(db_session) -> None:
    user = await _user_by_email(db_session, "director@example.com")
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)
    kpi = snap.kpi
    assert kpi.new_orders.value >= 0
    assert kpi.completed.value >= 0
    assert kpi.returned.value >= 0
    assert kpi.pending_approval.value >= 0
    assert kpi.open_critical_high_issues.value >= 0


async def test_wip_pipeline_total_matches_sum_of_stages(db_session) -> None:
    user = await _user_by_email(db_session, "director@example.com")
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)
    p = snap.wip_pipeline
    assert p.total == (
        p.waiting_dispatch[0]
        + p.dispatched[0]
        + p.in_progress[0]
        + p.awaiting_handoff[0]
        + p.done[0]
        + p.terminated[0]
    )


async def test_machine_heatmap_in_use_count_bounded(db_session) -> None:
    user = await _user_by_email(db_session, "director@example.com")
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)
    m = snap.machines
    assert m.in_use_count <= m.total_count
    assert 0 <= m.avg_utilization_pct <= 100


# --------------------------------------------------------------- lab_supervisor


async def test_lab_supervisor_sees_completions_and_no_leaderboard(db_session) -> None:
    user = await _user_by_email(db_session, "supervisor@example.com")  # LAB-A
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)

    assert snap.viewer_role == "lab_supervisor"
    assert snap.viewer_lab == "LAB-A"
    assert snap.lab_leaderboard is None
    assert snap.recent_completions is not None


async def test_lab_supervisor_machines_are_scoped_to_own_lab(db_session) -> None:
    """LAB-A's seeded display name is 材料分析實驗室. Every widget's
    ``lab_name`` is the display name, so the supervisor's machine grid
    should only contain that one name."""
    user = await _user_by_email(db_session, "supervisor@example.com")  # LAB-A
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)
    for machines in snap.machines.by_lab.values():
        for grid in machines:
            assert grid.lab_name == "材料分析實驗室"


# --------------------------------------------------------------- system_admin


async def test_system_admin_treated_as_cross_lab(db_session) -> None:
    """Sysadmin sees everything (wildcard ``*`` permission) → general_supervisor
    rendering."""
    user = await _user_by_email(db_session, "admin@example.com")
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)
    assert snap.viewer_role == "general_supervisor"
    assert snap.viewer_lab is None


# --------------------------------------------------------------- shape


async def test_triage_has_at_most_5_items(db_session) -> None:
    user = await _user_by_email(db_session, "director@example.com")
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)
    assert len(snap.triage) <= 5


async def test_recent_escalations_capped(db_session) -> None:
    user = await _user_by_email(db_session, "director@example.com")
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(user)
    assert len(snap.recent_escalations) <= 5
