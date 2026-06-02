"""Internal NotificationService paths not reachable via the public API:

* ``_dispatch_phone_callout`` — PHONE channel enqueues a Celery callout for
  recipients with a phone, and skips cleanly when none have one.
* ``mark_notification_answered`` — the TAS phone-pickup ack path: flips unread
  PHONE notifications to READ and acknowledges the source Issue (clearing
  ``next_escalation_time`` and stamping ``handled_at``).

These are driven through ``NotificationService`` + ``db_session`` directly.
Celery (``send_callout``) is monkeypatched so no broker is required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import (
    IssueStatus,
    IssueType,
    NotificationChannel,
    NotificationStatus,
)
from app.db.models.issues import Issue
from app.db.models.notifications import Notification
from app.db.models.users import User
from app.services.notifications import NotificationService

pytestmark = pytest.mark.asyncio


async def _me_id(client) -> UUID:
    return UUID((await client.get("/api/me")).json()["data"]["id"])


async def _lab_id(client, code: str) -> UUID:
    md = (await client.get("/api/master-data")).json()["data"]
    return UUID(next(lab["id"] for lab in md["labs"] if lab["code"] == code))


# ---------------------------------------------------------------------------
# _dispatch_phone_callout via notify(channels=[PHONE])
# ---------------------------------------------------------------------------


async def test_phone_channel_enqueues_callout_for_recipient_with_phone(
    engineer_a_client,
    admin_client,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """A PHONE notification for a recipient who has a phone enqueues exactly
    one Celery callout carrying their number and the issue tag."""
    import app.workers.phone_sender as phone_sender

    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    # Ensure the recipient has a phone on file.
    user = (await db_session.execute(select(User).where(User.id == eng_a_id))).scalar_one()
    user.phone = "0912345678"
    await db_session.commit()

    captured: dict = {}

    def _capture_delay(*, phones, title, body, tags):
        captured.update(phones=phones, title=title, body=body, tags=tags)

    monkeypatch.setattr(phone_sender.send_callout, "delay", _capture_delay)

    service = NotificationService(db_session)
    await service.notify(
        recipient_ids=[eng_a_id],
        lab_id=lab_a_id,
        source_type="issue",
        source_id="src-phone-1",
        title="phone alert",
        body="ring ring",
        channels=[NotificationChannel.IN_APP, NotificationChannel.PHONE],
    )

    assert captured["phones"] == ["0912345678"]
    assert captured["tags"] == ["issue:src-phone-1"]


async def test_phone_channel_skips_when_no_recipient_has_phone(
    engineer_b_client,
    admin_client,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """If no recipient has a phone, no callout is enqueued (but the in-app
    rows are still created)."""
    import app.workers.phone_sender as phone_sender

    eng_b_id = await _me_id(engineer_b_client)
    lab_b_id = await _lab_id(admin_client, "LAB-B")

    user = (await db_session.execute(select(User).where(User.id == eng_b_id))).scalar_one()
    user.phone = None
    await db_session.commit()

    called = {"n": 0}

    def _delay(**_kw):
        called["n"] += 1

    monkeypatch.setattr(phone_sender.send_callout, "delay", _delay)

    service = NotificationService(db_session)
    rows = await service.notify(
        recipient_ids=[eng_b_id],
        lab_id=lab_b_id,
        source_type="issue",
        source_id="src-phone-2",
        title="no-phone alert",
        channels=[NotificationChannel.PHONE],
    )

    assert called["n"] == 0
    # The PHONE notification row is still persisted even without a number.
    assert len(rows) == 1
    assert rows[0].channel == NotificationChannel.PHONE


async def test_notify_empty_recipients_is_noop(db_session: AsyncSession) -> None:
    service = NotificationService(db_session)
    result = await service.notify(
        recipient_ids=[],
        lab_id=UUID(int=0),
        source_type="issue",
        source_id="none",
        title="x",
    )
    assert result == []


async def test_notify_collapses_duplicate_recipients(
    engineer_a_client,
    admin_client,
    db_session: AsyncSession,
) -> None:
    """Duplicate recipient ids collapse to one row per (recipient, channel)."""
    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    service = NotificationService(db_session)
    rows = await service.notify(
        recipient_ids=[eng_a_id, eng_a_id, eng_a_id],
        lab_id=lab_a_id,
        source_type="issue",
        source_id="src-dup",
        title="dedupe",
        channels=[NotificationChannel.IN_APP],
    )
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# mark_notification_answered — TAS phone-pickup ack
# ---------------------------------------------------------------------------


async def test_mark_answered_flips_phone_rows_and_acks_issue(
    engineer_a_client,
    admin_client,
    db_session: AsyncSession,
) -> None:
    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    future = datetime.now(UTC) + timedelta(hours=1)
    issue = Issue(
        type=IssueType.ABNORMAL,
        target_type="machine",
        target_id="M-ANS",
        lab_id=lab_a_id,
        title="answered-test issue",
        status=IssueStatus.OPEN,
        next_escalation_time=future,
    )
    db_session.add(issue)
    await db_session.flush()
    issue_id = issue.id

    service = NotificationService(db_session)
    await service.notify(
        recipient_ids=[eng_a_id],
        lab_id=lab_a_id,
        source_type="issue",
        source_id=str(issue_id),
        title="phone alert",
        channels=[NotificationChannel.IN_APP, NotificationChannel.PHONE],
    )

    flipped = await service.mark_notification_answered(issue_id)
    # Exactly the one PHONE row flips (the IN_APP row is untouched).
    assert flipped == 1

    db_session.expire_all()
    refreshed = (await db_session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
    assert refreshed.status == IssueStatus.ACKNOWLEDGED
    assert refreshed.next_escalation_time is None
    assert refreshed.handled_at is not None

    # The PHONE notification is now READ; the IN_APP one stays UNREAD.
    notes = (
        (
            await db_session.execute(
                select(Notification).where(Notification.source_id == str(issue_id))
            )
        )
        .scalars()
        .all()
    )
    by_channel = {n.channel: n.status for n in notes}
    assert by_channel[NotificationChannel.PHONE] == NotificationStatus.READ
    assert by_channel[NotificationChannel.IN_APP] == NotificationStatus.UNREAD


async def test_mark_answered_no_phone_rows_returns_zero(
    admin_client,
    db_session: AsyncSession,
) -> None:
    """An issue with no PHONE notifications flips nothing but still acks the
    issue (clears escalation)."""
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    issue = Issue(
        type=IssueType.ABNORMAL,
        target_type="machine",
        target_id="M-ANS-0",
        lab_id=lab_a_id,
        title="answered-no-phone",
        status=IssueStatus.OPEN,
        next_escalation_time=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(issue)
    await db_session.flush()
    issue_id = issue.id

    service = NotificationService(db_session)
    flipped = await service.mark_notification_answered(issue_id)
    assert flipped == 0

    db_session.expire_all()
    refreshed = (await db_session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
    assert refreshed.status == IssueStatus.ACKNOWLEDGED
    assert refreshed.next_escalation_time is None


async def test_mark_answered_does_not_downgrade_closed_issue(
    engineer_a_client,
    admin_client,
    db_session: AsyncSession,
) -> None:
    """A stray pickup on an already-CLOSED issue must not reopen/downgrade it
    to ACKNOWLEDGED."""
    eng_a_id = await _me_id(engineer_a_client)
    lab_a_id = await _lab_id(admin_client, "LAB-A")

    issue = Issue(
        type=IssueType.ABNORMAL,
        target_type="machine",
        target_id="M-CLOSED",
        lab_id=lab_a_id,
        title="closed-issue",
        status=IssueStatus.CLOSED,
    )
    db_session.add(issue)
    await db_session.flush()
    issue_id = issue.id

    service = NotificationService(db_session)
    await service.notify(
        recipient_ids=[eng_a_id],
        lab_id=lab_a_id,
        source_type="issue",
        source_id=str(issue_id),
        title="late pickup",
        channels=[NotificationChannel.PHONE],
    )

    await service.mark_notification_answered(issue_id)

    db_session.expire_all()
    refreshed = (await db_session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
    assert refreshed.status == IssueStatus.CLOSED
