"""Router-level integration tests for ``/api/dashboard``.

We don't exercise the SSE stream here — connecting to a Redis-backed
EventSource and asserting on the stream is brittle in unit tests. The
publisher's behavior is decoupled (best-effort log-and-swallow) and is
covered separately when the publish hooks land. These tests focus on the
synchronous snapshot endpoint, auth gating, and role projection.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_get_dashboard_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/dashboard")
    assert res.status_code == 401


async def test_get_dashboard_plant_user_forbidden(plant_user_client: AsyncClient) -> None:
    """plant_user has no ``dashboard:read`` → 403, not 200 with sneaky data."""
    res = await plant_user_client.get("/api/dashboard")
    assert res.status_code == 403


async def test_get_dashboard_as_lab_supervisor(supervisor_a_client: AsyncClient) -> None:
    res = await supervisor_a_client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    snap = body["data"]
    assert snap["viewer_role"] == "lab_supervisor"
    # LAB-A supervisor is scoped to their own lab.
    assert snap["viewer_lab"] == "LAB-A"
    # Recent completions is the lab_supervisor's Col 3 panel.
    assert snap["recent_completions"] is not None
    # Lab leaderboard is the general_supervisor's panel and must be null here.
    assert snap["lab_leaderboard"] is None


async def test_get_dashboard_as_general_supervisor(director_client: AsyncClient) -> None:
    res = await director_client.get("/api/dashboard")
    assert res.status_code == 200
    snap = res.json()["data"]
    assert snap["viewer_role"] == "general_supervisor"
    assert snap["viewer_lab"] is None
    # Leaderboard non-null; completions null.
    assert snap["lab_leaderboard"] is not None
    assert snap["recent_completions"] is None


async def test_get_dashboard_response_shape(director_client: AsyncClient) -> None:
    """Smoke check that every widget key exists on the wire."""
    res = await director_client.get("/api/dashboard")
    snap = res.json()["data"]
    for key in (
        "viewer_role",
        "viewer_lab",
        "generated_at",
        "kpi",
        "machines",
        "wip_pipeline",
        "triage",
        "recent_escalations",
        "recent_completions",
        "lab_leaderboard",
    ):
        assert key in snap, f"missing top-level key {key!r}"
    # KPI bar has exactly five cards.
    kpi = snap["kpi"]
    assert set(kpi.keys()) == {
        "new_orders",
        "completed",
        "returned",
        "pending_approval",
        "open_critical_high_issues",
    }
    for card in kpi.values():
        assert "value" in card
        assert "delta_24h" in card
        assert "threshold_color" in card


async def test_get_dashboard_pipeline_has_six_stages(director_client: AsyncClient) -> None:
    res = await director_client.get("/api/dashboard")
    pipeline = res.json()["data"]["wip_pipeline"]
    for stage in (
        "waiting_dispatch",
        "dispatched",
        "in_progress",
        "awaiting_handoff",
        "done",
        "terminated",
    ):
        assert stage in pipeline
        # Each stage is a [count, delta] pair.
        assert isinstance(pipeline[stage], list)
        assert len(pipeline[stage]) == 2
