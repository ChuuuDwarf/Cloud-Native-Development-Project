"""Celery tasks: escalate overdue issues per hard-coded rules.

Two entry points, both driving the same per-issue mutation logic:

- ``escalate_specific_issue`` (Option C primary driver): ETA-scheduled at
  ``apply_async(eta=issue.next_escalation_time)`` for precision — each
  issue gets its own task that fires at exactly the right moment.
  Re-arms itself on success by scheduling the next ETA hop if the new
  level still has a rule.
- ``scan_and_escalate`` (Beat safety net every 60s): sweeps any issue
  whose ``next_escalation_time`` is in the past but didn't get picked up
  by an ETA task (worker restart, lost broker message, etc.).

Both call the shared ``_escalate_one_issue`` helper so the mutation +
notification behaviour is defined exactly once.

- Hard-coded escalation table (richer rules will eventually move into
  ``system_settings.alertRules``):
    level 0 → bump to level 1, notify lab_supervisor of the lab,
              rearm timer for level-2 escalation.
    level 1 → bump to level 2, notify general_supervisor (大主管, cross-lab),
              terminal — no further escalation.
- Per overdue issue: bump ``escalation_level``, flip ``status`` to
  ``escalated``, rearm or clear ``next_escalation_time``, then call
  ``NotificationService.notify`` to fan out the alert.
- ``recipient_scope`` switches between per-lab and global lookups so
  lab-less roles (general_supervisor) get notified the way they're seeded
  (no ``user.lab_id``); see ``recipients_for_global_role``.
- Celery is sync; we run the async body inside ``asyncio.run`` and open a
  fresh ``AsyncSessionLocal`` per task.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.common.enums import IssueStatus, NotificationChannel
from app.common.recipients import recipients_for_global_role, recipients_for_role_in_lab
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.db.models.issues import Issue
from app.db.models.labs import Lab
from app.modules.dashboard.publisher import publish_new_escalation
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)

# How long to wait between escalation hops once a level fires. Kept short so
# the demo is obvious; production tuning will live in system_settings.
RE_ESCALATION_DELAY = timedelta(seconds=10)

# Maps current escalation_level → behaviour. Levels not present here are
# terminal (no further escalation). ``recipient_scope`` is "lab" for
# lab-bound roles (looked up via ``user.lab_id == issue.lab_id``) or
# "global" for cross-lab roles like general_supervisor.
ESCALATION_RULES: dict[int, dict[str, Any]] = {
    0: {
        "next_level": 1,
        "notify_role": "lab_supervisor",
        "recipient_scope": "lab",
    },
    1: {
        "next_level": 2,
        "notify_role": "general_supervisor",
        "recipient_scope": "global",
    },
}


async def _escalate_one_issue(
    issue: Issue,
    session: Any,
    notification_service: NotificationService,
    now: datetime,
) -> bool:
    """Apply one escalation hop to ``issue``.

    Returns True if the issue was escalated, False if it was skipped
    (terminal level, no rule, or failure that triggered a rollback).
    Callers are responsible for the surrounding loop / commit cadence;
    this helper performs its own rollback on failure so one bad issue
    cannot abort a batch in the Beat scan.
    """
    rule = ESCALATION_RULES.get(issue.escalation_level)
    if rule is None:
        return False

    new_level = rule["next_level"]

    try:
        issue.escalation_level = new_level
        issue.status = IssueStatus.ESCALATED
        # Rearm if the *new* level has its own rule (so the next hop
        # can fire), otherwise terminate so Beat stops re-picking
        # this issue. Read the table at runtime — keeps a future
        # rule addition (level 2 → 3) Just Working.
        if new_level in ESCALATION_RULES:
            issue.next_escalation_time = now + RE_ESCALATION_DELAY
        else:
            issue.next_escalation_time = None

        # Lab-bound vs global recipient lookup. Lab-bound roles
        # (lab_supervisor) require user.lab_id; global roles
        # (general_supervisor) are intentionally lab-less in seed.
        if rule["recipient_scope"] == "global":
            recipient_ids = await recipients_for_global_role(session, role_name=rule["notify_role"])
        else:
            recipient_ids = await recipients_for_role_in_lab(
                session, lab_id=issue.lab_id, role_name=rule["notify_role"]
            )

        if not recipient_ids:
            # No recipient in that scope — escalation still happens
            # (issue is now in ESCALATED state) but no one was alerted.
            # Loud so ops can fix the staffing / role config.
            # Only include lab=... for lab-scoped lookups; the global
            # branch doesn't look at lab_id and including it would
            # falsely imply we did.
            lab_suffix = f" lab={issue.lab_id}" if rule["recipient_scope"] == "lab" else ""
            logger.warning(
                "escalated issue=%s to level=%d but NO recipients found " "for role=%s scope=%s%s",
                issue.id,
                new_level,
                rule["notify_role"],
                rule["recipient_scope"],
                lab_suffix,
            )

        # notify() commits, which also flushes our pending issue mutations.
        # Escalation rings the supervisor's phone too (per Sprint 3d).
        await notification_service.notify(
            recipient_ids=recipient_ids,
            lab_id=issue.lab_id,
            source_type="issue",
            source_id=str(issue.id),
            title=f"[升級 Lv{new_level}] {issue.title}",
            body=issue.description,
            severity=issue.severity,
            channels=[NotificationChannel.IN_APP, NotificationChannel.PHONE],
        )
    except Exception:
        # One bad issue must not abort the whole batch. Roll back this
        # iteration's pending mutations; next Beat tick (safety net) will
        # retry because the issue's next_escalation_time is still in the past.
        logger.exception("escalation failed for issue=%s, rolling back", issue.id)
        await session.rollback()
        return False

    logger.info(
        "escalated issue=%s to level=%d, notified %d recipient(s)",
        issue.id,
        new_level,
        len(recipient_ids),
    )

    # Best-effort dashboard SSE fanout — failures here must not abort the
    # escalation (notify() already committed above). Publisher swallows its
    # own Redis errors; we wrap the lab lookup for the same reason.
    # NOTE: publisher channels are keyed by Lab.code (ASCII), not Lab.name
    # (display name), so the SSE handler — which subscribes off
    # CurrentUser.lab_code — actually receives the event.
    try:
        lab_code = await session.scalar(select(Lab.code).where(Lab.id == issue.lab_id))
        await publish_new_escalation(lab_code)
    except Exception:
        logger.exception("dashboard publish_new_escalation failed issue=%s", issue.id)

    return True


async def _scan_and_escalate_async() -> dict[str, int]:
    now = datetime.now(UTC)
    escalated = 0

    async with AsyncSessionLocal() as session:
        # ESCALATED is kept in the filter so a future re-escalation rule
        # (level 1 → 2 etc.) can re-fire by setting next_escalation_time
        # on an already-ESCALATED issue without changing this query.
        stmt = select(Issue).where(
            Issue.status.in_([IssueStatus.OPEN, IssueStatus.ASSIGNED, IssueStatus.ESCALATED]),
            Issue.next_escalation_time.is_not(None),
            Issue.next_escalation_time <= now,
        )
        issues = list((await session.execute(stmt)).scalars().all())

        notification_service = NotificationService(session)

        for issue in issues:
            if await _escalate_one_issue(issue, session, notification_service, now):
                escalated += 1

    return {"escalated": escalated}


async def _escalate_specific_async(issue_id: str) -> dict[str, Any]:
    """Single-issue escalation body invoked by ETA-scheduled task.

    Re-validates the issue is still escalatable at firing time so an
    already-acknowledged / closed issue silently no-ops, and a task that
    fires slightly early (broker scheduling jitter) waits for the Beat
    sweep instead of escalating prematurely.
    """
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as session:
        # 2s buffer absorbs broker / worker scheduling jitter: an ETA task
        # that fires a hair early still escalates instead of bouncing.
        # Anything earlier than that falls through to "not due" and the
        # Beat safety net will pick it up.
        stmt = select(Issue).where(
            Issue.id == issue_id,
            Issue.status.in_([IssueStatus.OPEN, IssueStatus.ASSIGNED, IssueStatus.ESCALATED]),
            Issue.next_escalation_time.is_not(None),
            Issue.next_escalation_time <= now + timedelta(seconds=2),
        )
        issue = (await session.execute(stmt)).scalar_one_or_none()

        if issue is None:
            # Already ACKNOWLEDGED/CLOSED, or fired too early — leave it
            # for either the next ETA task or the Beat safety net.
            return {"escalated": 0, "skipped": "not_due_or_terminal"}

        notification_service = NotificationService(session)

        if not await _escalate_one_issue(issue, session, notification_service, now):
            # Helper already logged + rolled back; Beat will retry.
            return {"escalated": 0, "skipped": "escalation_failed"}

        # Re-arm the per-issue ETA chain. If the new level still has a
        # rule, next_escalation_time was just set by the helper; schedule
        # the next hop precisely at that time. Terminal levels leave
        # next_escalation_time = None and we stop scheduling.
        if issue.next_escalation_time is not None:
            escalate_specific_issue.apply_async(
                args=[str(issue.id)],
                eta=issue.next_escalation_time,
            )

        return {"escalated": 1}


@celery_app.task(name="app.workers.escalation.scan_and_escalate")
def scan_and_escalate() -> dict[str, int]:
    """Celery entry point — Beat safety-net scan (every 60s)."""
    return asyncio.run(_scan_and_escalate_async())


@celery_app.task(name="app.workers.escalation.escalate_specific_issue")
def escalate_specific_issue(issue_id: str) -> dict[str, Any]:
    """ETA-based single-issue escalation. Fires at exactly next_escalation_time."""
    return asyncio.run(_escalate_specific_async(issue_id))
