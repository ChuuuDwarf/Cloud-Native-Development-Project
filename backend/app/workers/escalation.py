"""Celery task: scan open issues and escalate per hard-coded rules.

Beat-scheduled every minute (see ``app.core.celery_app.beat_schedule``).
Sprint 3c implementation:

- Hard-coded escalation table (one rule today; later sourced from
  ``system_settings.alertRules``):
    level 0  →  after 5 min, bump to level 1, notify supervisors of the lab.
    level 1+ →  no further escalation rule, leave alone.
- Per overdue issue: bump ``escalation_level``, flip ``status`` to
  ``escalated``, clear ``next_escalation_time`` (so we don't re-fire),
  then call ``NotificationService.notify`` to fan out the alert.
- Celery is sync; we run the async body inside ``asyncio.run`` and open a
  fresh ``AsyncSessionLocal`` per scan.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.common.enums import IssueStatus, NotificationChannel
from app.common.recipients import recipients_for_role_in_lab
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.db.models.issues import Issue
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)

# Maps current escalation_level → behaviour. Levels not present here are
# terminal (no further escalation). Sprint 3c keeps it tiny so the demo is
# obvious; richer rules belong in system_settings later.
ESCALATION_RULES: dict[int, dict[str, Any]] = {
    0: {"next_level": 1, "notify_role": "lab_supervisor"},
}


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
            rule = ESCALATION_RULES.get(issue.escalation_level)
            if rule is None:
                continue

            new_level = rule["next_level"]

            try:
                issue.escalation_level = new_level
                issue.status = IssueStatus.ESCALATED
                # Terminal rule: no further escalation, stop re-firing.
                issue.next_escalation_time = None

                recipient_ids = await recipients_for_role_in_lab(
                    session, lab_id=issue.lab_id, role_name=rule["notify_role"]
                )

                if not recipient_ids:
                    # No supervisor in that lab — escalation still happens (issue
                    # is now in ESCALATED state) but no one was alerted. Loud so
                    # ops can fix the lab's staffing config.
                    logger.warning(
                        "escalated issue=%s to level=%d but NO recipients found "
                        "for role=%s in lab=%s",
                        issue.id,
                        new_level,
                        rule["notify_role"],
                        issue.lab_id,
                    )

                # notify() commits, which also flushes our pending issue mutations.
                await notification_service.notify(
                    recipient_ids=recipient_ids,
                    lab_id=issue.lab_id,
                    source_type="issue",
                    source_id=str(issue.id),
                    title=f"[升級 Lv{new_level}] {issue.title}",
                    body=issue.description,
                    severity=issue.severity,
                    channels=[NotificationChannel.IN_APP],
                )
            except Exception:
                # One bad issue must not abort the whole batch. Roll back this
                # iteration's pending mutations; next Beat tick will retry
                # because the issue's next_escalation_time is still in the past.
                logger.exception("escalation failed for issue=%s, rolling back", issue.id)
                await session.rollback()
                continue

            escalated += 1
            logger.info(
                "escalated issue=%s to level=%d, notified %d recipient(s)",
                issue.id,
                new_level,
                len(recipient_ids),
            )

    return {"escalated": escalated}


@celery_app.task(name="app.workers.escalation.scan_and_escalate")
def scan_and_escalate() -> dict[str, int]:
    """Celery entry point — wraps the async scan in ``asyncio.run``."""
    return asyncio.run(_scan_and_escalate_async())
