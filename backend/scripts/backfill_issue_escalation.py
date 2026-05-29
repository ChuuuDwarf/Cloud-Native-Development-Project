"""One-off backfill: arm next_escalation_time on issues created before Sprint 3c.

Issues created before the escalation pipeline landed have
``next_escalation_time = NULL`` and will never be picked up by the Celery
worker. This script sets every still-open NULL one to ``now() + 10s`` so the
next Beat tick can escalate them.

Idempotent: only touches rows where ``next_escalation_time IS NULL`` AND
``status IN ('open', 'assigned')``. Safe to re-run.

Usage::

    cd backend && source venv/bin/activate
    python -m scripts.backfill_issue_escalation
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.common.enums import IssueStatus
from app.core.database import AsyncSessionLocal
from app.db.models.issues import Issue


async def main() -> None:
    deadline = datetime.now(UTC) + timedelta(seconds=10)
    async with AsyncSessionLocal() as session:
        stmt = (
            update(Issue)
            .where(
                Issue.next_escalation_time.is_(None),
                Issue.status.in_([IssueStatus.OPEN, IssueStatus.ASSIGNED]),
            )
            .values(next_escalation_time=deadline)
        )
        result = await session.execute(stmt)
        await session.commit()
        print(
            f"backfilled {result.rowcount} issue(s) -> next_escalation_time={deadline.isoformat()}"
        )


if __name__ == "__main__":
    asyncio.run(main())
