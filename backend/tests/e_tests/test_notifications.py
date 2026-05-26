"""Tests for /api/notifications + recipient scope."""

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import NotificationChannel, Severity
from app.services.notifications import NotificationService

# ---------------------------------------------------------------------------
# Helpers — extract id/lab from /api/me + /api/master-data.
# ---------------------------------------------------------------------------


async def _me_id(client: AsyncClient) -> UUID:
    res = await client.get("/api/me")
    return UUID(res.json()["data"]["id"])


async def _lab_id(client: AsyncClient, code: str) -> UUID:
    md = (await client.get("/api/master-data")).json()["data"]
    return UUID(next(lab["id"] for lab in md["labs"] if lab["code"] == code))


async def _seed_notification(
    session: AsyncSession,
    *,
    recipient_id: UUID,
    lab_id: UUID,
    title: str = "test notification",
    severity: Severity = Severity.MEDIUM,
    channels: list[NotificationChannel] | None = None,
) -> list[UUID]:
    """Insert notification rows via NotificationService and return their ids."""
    service = NotificationService(session)
    rows = await service.notify(
        recipient_ids=[recipient_id],
        lab_id=lab_id,
        source_type="issue",
        source_id="seed-test-source",
        title=title,
        severity=severity,
        channels=channels,
    )
    return [row.id for row in rows]


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_list_notifications_is_401(client: AsyncClient) -> None:
    response = await client.get("/api/notifications")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_mark_read_is_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/notifications/actions",
        json={"ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List / get — recipient scope is the security-critical behaviour.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engineer_a_sees_only_own_notifications(
    engineer_a_client: AsyncClient,
    engineer_b_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    eng_a_id = await _me_id(engineer_a_client)
    eng_b_id = await _me_id(engineer_b_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")
    lab_b_id = await _lab_id(admin_client, "LAB-B")

    await _seed_notification(
        db_session, recipient_id=eng_a_id, lab_id=lab_a_id, title="for engineer A"
    )
    await _seed_notification(
        db_session, recipient_id=eng_b_id, lab_id=lab_b_id, title="for engineer B"
    )

    list_a = (await engineer_a_client.get("/api/notifications")).json()
    titles_a = {n["title"] for n in list_a["items"]}
    assert "for engineer A" in titles_a
    assert "for engineer B" not in titles_a


@pytest.mark.asyncio
async def test_admin_cannot_see_other_users_notifications(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Admin role has no privilege over other users' inboxes."""
    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    notification_ids = await _seed_notification(
        db_session, recipient_id=eng_a_id, lab_id=lab_a_id, title="private to engineer A"
    )

    admin_view = (await admin_client.get("/api/notifications")).json()
    admin_titles = {n["title"] for n in admin_view["items"]}
    assert "private to engineer A" not in admin_titles

    response = await admin_client.get(f"/api/notifications/{notification_ids[0]}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_notification_is_404(admin_client: AsyncClient) -> None:
    response = await admin_client.get("/api/notifications/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_filter_by_severity(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    await _seed_notification(
        db_session,
        recipient_id=eng_a_id,
        lab_id=lab_a_id,
        title="filter-low",
        severity=Severity.LOW,
    )
    await _seed_notification(
        db_session,
        recipient_id=eng_a_id,
        lab_id=lab_a_id,
        title="filter-critical",
        severity=Severity.CRITICAL,
    )

    resp = await engineer_a_client.get("/api/notifications", params={"severity": "critical"})
    titles = {n["title"] for n in resp.json()["items"]}
    assert "filter-critical" in titles
    assert "filter-low" not in titles


# ---------------------------------------------------------------------------
# Mark-as-read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read_flips_status_and_returns_count(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    ids = await _seed_notification(
        db_session, recipient_id=eng_a_id, lab_id=lab_a_id, title="to be marked"
    )

    resp = await engineer_a_client.post(
        "/api/notifications/actions",
        json={"ids": [str(nid) for nid in ids]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["markedCount"] == len(ids)
    assert body["skippedIds"] == []

    fetched = await engineer_a_client.get(f"/api/notifications/{ids[0]}")
    assert fetched.json()["data"]["status"] == "read"
    assert fetched.json()["data"]["readAt"] is not None


@pytest.mark.asyncio
async def test_mark_read_silently_skips_others_ids(
    engineer_a_client: AsyncClient,
    engineer_b_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Skipping (not 404) prevents leaking existence of others' notifications."""
    eng_b_id = await _me_id(engineer_b_client)
    lab_b_id = await _lab_id(admin_client, "LAB-B")

    others_ids = await _seed_notification(
        db_session, recipient_id=eng_b_id, lab_id=lab_b_id, title="not for A"
    )

    resp = await engineer_a_client.post(
        "/api/notifications/actions",
        json={"ids": [str(nid) for nid in others_ids]},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["markedCount"] == 0
    assert set(body["skippedIds"]) == {str(nid) for nid in others_ids}


@pytest.mark.asyncio
async def test_mark_read_already_read_goes_to_skipped(
    engineer_a_client: AsyncClient,
    admin_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    ids = await _seed_notification(
        db_session, recipient_id=eng_a_id, lab_id=lab_a_id, title="double-mark"
    )
    payload = {"ids": [str(nid) for nid in ids]}

    first = await engineer_a_client.post("/api/notifications/actions", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["markedCount"] == len(ids)

    second = await engineer_a_client.post("/api/notifications/actions", json=payload)
    assert second.json()["data"]["markedCount"] == 0
    assert set(second.json()["data"]["skippedIds"]) == {str(nid) for nid in ids}


@pytest.mark.asyncio
async def test_mark_read_empty_ids_is_422(engineer_a_client: AsyncClient) -> None:
    """Schema enforces min_length=1 before the endpoint body runs."""
    resp = await engineer_a_client.post("/api/notifications/actions", json={"ids": []})
    assert resp.status_code == 422
