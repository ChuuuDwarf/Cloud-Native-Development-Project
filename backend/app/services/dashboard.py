"""Aggregation service for ``GET /api/dashboard``.

All counts respect the caller's lab scope via
:func:`app.common.dependencies.scope.apply_lab_scope` — the same helper the
issues / notifications repos use, so a new role added to the seed Just
Works (system_admin → all, lab_supervisor / lab_engineer → own lab,
others → ForbiddenError instead of silent fall-through).

Implementation note: each widget is a small standalone query so the SQL is
easy to read in logs. The dashboard is read-heavy and rarely-fetched (a
supervisor opens the page, not in a hot loop), so we trade chattiness for
clarity. If this becomes hot, fold into a CTE.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.common.dependencies.scope import apply_lab_scope
from app.common.enums import IssueStatus, NotificationStatus, Severity
from app.core.database import get_db
from app.db.models.issues import Issue
from app.db.models.labs import Lab
from app.db.models.notifications import Notification

# Statuses that count as "open" for dashboard purposes (anything not closed).
OPEN_ISSUE_STATUSES = [IssueStatus.OPEN, IssueStatus.ASSIGNED, IssueStatus.ESCALATED]

# How many escalations to surface in the at-a-glance panel.
RECENT_ESCALATIONS_LIMIT = 5


def _start_of_today_utc() -> datetime:
    """Today's 00:00 in UTC. ``Issue.created_at`` / ``updated_at`` are stored
    as ``DateTime(timezone=True)`` so this comparison is timezone-safe."""
    now = datetime.now(UTC)
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


class DashboardService:
    """Read-only aggregations for the supervisor dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_snapshot(self, user: CurrentUser) -> dict[str, Any]:
        return {
            "issues": await self._issues_summary(user),
            "unread_notifications": await self._unread_notifications_count(user),
            "by_lab": await self._by_lab_breakdown(user),
            "recent_escalations": await self._recent_escalations(user),
        }

    # ----- widget queries -----

    async def _issues_summary(self, user: CurrentUser) -> dict[str, Any]:
        today = _start_of_today_utc()

        # Pull only the small slice we need (status, severity, created_at,
        # updated_at) so Python-side bucketing stays cheap even at a few
        # thousand open issues — beyond that, switch to SQL FILTER aggregates.
        stmt = select(Issue.status, Issue.severity, Issue.created_at, Issue.updated_at).where(
            Issue.status.in_(OPEN_ISSUE_STATUSES)
        )
        stmt = apply_lab_scope(stmt, user, Issue.lab_id)

        rows = list((await self._session.execute(stmt)).all())

        # Seed every known Severity to 0 so the frontend never gets a
        # missing-key surprise; ignore unknown values (drift / stale rows).
        by_severity: dict[str, int] = {s.value: 0 for s in Severity}
        created_today = 0
        escalated_today = 0
        for status, severity, created_at, updated_at in rows:
            if severity in by_severity:
                by_severity[severity] += 1
            if created_at >= today:
                created_today += 1
            if status == IssueStatus.ESCALATED and updated_at >= today:
                escalated_today += 1

        return {
            "total_open": len(rows),
            "by_severity": by_severity,
            "created_today": created_today,
            "escalated_today": escalated_today,
        }

    async def _unread_notifications_count(self, user: CurrentUser) -> int:
        """Scoped by recipient_id; lab scope is implicit (a user only ever
        receives their own notifications)."""
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == user.id,
                Notification.status == NotificationStatus.UNREAD,
            )
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def _by_lab_breakdown(self, user: CurrentUser) -> list[dict[str, Any]]:
        """One row per lab visible to the caller. LEFT JOIN issues so labs
        with zero issues still appear (avoids holes on the leaderboard).
        ``apply_lab_scope`` on ``Lab.id`` keeps supervisors to their lab and
        admins to all labs."""
        stmt = (
            select(
                Lab.id,
                Lab.code,
                Lab.name,
                func.count(Issue.id)
                .filter(Issue.status.in_(OPEN_ISSUE_STATUSES))
                .label("open_issues"),
                func.count(Issue.id)
                .filter(Issue.status == IssueStatus.ESCALATED)
                .label("escalated_issues"),
            )
            .select_from(Lab)
            .join(Issue, Issue.lab_id == Lab.id, isouter=True)
            .group_by(Lab.id, Lab.code, Lab.name)
            .order_by(Lab.code)
        )
        stmt = apply_lab_scope(stmt, user, Lab.id)

        result = await self._session.execute(stmt)
        return [
            {
                "lab_id": row.id,
                "lab_code": row.code,
                "lab_name": row.name,
                "open_issues": int(row.open_issues),
                "escalated_issues": int(row.escalated_issues),
            }
            for row in result.all()
        ]

    async def _recent_escalations(self, user: CurrentUser) -> list[dict[str, Any]]:
        """Last N escalated issues — newest first. Useful for at-a-glance
        triage. WHERE-then-ORDER/LIMIT order matters for readability — the
        scope filter is applied before sort/limit."""
        stmt = select(Issue).where(Issue.status == IssueStatus.ESCALATED)
        stmt = apply_lab_scope(stmt, user, Issue.lab_id)
        stmt = stmt.order_by(Issue.updated_at.desc()).limit(RECENT_ESCALATIONS_LIMIT)

        items = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "id": issue.id,
                "title": issue.title,
                "severity": issue.severity,
                "escalation_level": issue.escalation_level,
                "lab_id": issue.lab_id,
                "updated_at": issue.updated_at,
            }
            for issue in items
        ]


async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardService:
    return DashboardService(session)
