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
from app.common.dependencies.scope import apply_lab_scope, resolve_user_lab_codes
from app.common.enums import IssueStatus, MachineStatus, NotificationStatus, Severity
from app.core.database import get_db
from app.core.order_enums import OrderStatus
from app.db.models.issues import Issue
from app.db.models.labs import Lab
from app.db.models.machines import Machine
from app.db.models.notifications import Notification
from app.db.models.order_management import OrderItemModel

# Statuses that count as "open" for dashboard purposes (anything not closed).
OPEN_ISSUE_STATUSES = [IssueStatus.OPEN, IssueStatus.ASSIGNED, IssueStatus.ESCALATED]

# How many escalations to surface in the at-a-glance panel.
RECENT_ESCALATIONS_LIMIT = 5

# Machine.status is stored as Chinese strings in the DB (C 組 schema choice).
# Map to the canonical English MachineStatus enum so the wire format matches
# the rest of the API. Unknown DB values fall through to the raw string so
# we don't lie to the frontend; they'll show as "other".
MACHINE_STATUS_CN_TO_EN: dict[str, str] = {
    "閒置": MachineStatus.IDLE.value,
    "使用中": MachineStatus.IN_USE.value,
    "保養中": MachineStatus.MAINTENANCE.value,
    "故障中": MachineStatus.FAULTY.value,
    "停用": MachineStatus.DISABLED.value,
}

# Order pipeline groupings — collapse 18 statuses into 5 supervisor-relevant
# buckets so the dashboard tells a story. Anything not listed is "other".
ORDER_STATUS_TO_BUCKET: dict[str, str] = {
    OrderStatus.DRAFT.value: "draft",
    OrderStatus.PENDING_APPROVAL.value: "pending_approval",
    OrderStatus.APPROVED.value: "in_pipeline",
    OrderStatus.WAITING_SAMPLE.value: "in_pipeline",
    OrderStatus.SAMPLE_DELIVERED.value: "in_pipeline",
    OrderStatus.SAMPLE_RECEIVED.value: "in_pipeline",
    OrderStatus.RECEIVED.value: "in_pipeline",
    OrderStatus.SPLIT.value: "in_pipeline",
    OrderStatus.SCHEDULED.value: "in_pipeline",
    OrderStatus.IN_PROGRESS.value: "in_progress",
    OrderStatus.WAITING_RESULT_CONFIRM.value: "in_progress",
    OrderStatus.COMPLETED.value: "completed",
    OrderStatus.WAITING_REPORT_RETURN.value: "completed",
    OrderStatus.WAITING_PICKUP.value: "completed",
    OrderStatus.READY_FOR_PICKUP.value: "completed",
    OrderStatus.CLOSED.value: "closed",
    OrderStatus.RETURNED.value: "blocked",
    OrderStatus.REJECTED.value: "blocked",
    OrderStatus.CANCELLED.value: "blocked",
}
ORDER_BUCKETS = [
    "draft",
    "pending_approval",
    "in_pipeline",
    "in_progress",
    "completed",
    "closed",
    "blocked",
]


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
        # Resolve lab codes once and pass into the string-lab widgets
        # (machines, orders use "LAB-A" strings, not UUID FKs). None means
        # "see all labs" (admin / general_supervisor).
        lab_codes = await resolve_user_lab_codes(self._session, user)
        return {
            "issues": await self._issues_summary(user),
            "unread_notifications": await self._unread_notifications_count(user),
            "by_lab": await self._by_lab_breakdown(user),
            "recent_escalations": await self._recent_escalations(user),
            "machines": await self._machines_summary(lab_codes),
            "orders": await self._orders_summary(lab_codes),
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

    async def _machines_summary(self, lab_codes: list[str] | None) -> dict[str, Any]:
        """Counts of machines grouped by canonical English status, plus a
        per-lab breakdown for the leaderboard panel.

        ``lab_codes is None`` ⇒ no lab filter (admin / general_supervisor).
        Single-element list ⇒ supervisor sees only their lab.
        """
        # Pull the small slice; bucketing in Python keeps the CN→EN map in
        # one place and lets us tolerate stray status values.
        stmt = select(Machine.lab, Machine.status, Machine.utilization)
        if lab_codes is not None:
            stmt = stmt.where(Machine.lab.in_(lab_codes))

        rows = list((await self._session.execute(stmt)).all())

        # Seed every known English status so frontend never gets a missing key.
        by_status: dict[str, int] = {s.value: 0 for s in MachineStatus}
        by_lab: dict[str, dict[str, int]] = {}
        total = len(rows)
        utilization_sum = 0
        for lab, status_cn, util in rows:
            status_en = MACHINE_STATUS_CN_TO_EN.get(status_cn, status_cn)
            if status_en in by_status:
                by_status[status_en] += 1
            bucket = by_lab.setdefault(lab, {s.value: 0 for s in MachineStatus})
            if status_en in bucket:
                bucket[status_en] += 1
            utilization_sum += util or 0

        avg_util = round(utilization_sum / total, 1) if total else 0.0

        return {
            "total": total,
            "by_status": by_status,
            "avg_utilization": avg_util,
            "by_lab": [
                {"lab_code": lab, "by_status": statuses} for lab, statuses in sorted(by_lab.items())
            ],
        }

    async def _orders_summary(self, lab_codes: list[str] | None) -> dict[str, Any]:
        """Counts of order ITEMS grouped into supervisor-relevant buckets
        (draft / pending_approval / in_pipeline / in_progress / completed /
        closed / blocked). Item-level instead of order-level because one
        order can span multiple labs and we want per-lab visibility."""
        stmt = select(OrderItemModel.lab_id, OrderItemModel.status)
        if lab_codes is not None:
            stmt = stmt.where(OrderItemModel.lab_id.in_(lab_codes))

        rows = list((await self._session.execute(stmt)).all())

        by_bucket: dict[str, int] = dict.fromkeys(ORDER_BUCKETS, 0)
        by_lab: dict[str, dict[str, int]] = {}
        for lab, status in rows:
            bucket = ORDER_STATUS_TO_BUCKET.get(status, "other")
            if bucket in by_bucket:
                by_bucket[bucket] += 1
            else:
                by_bucket[bucket] = by_bucket.get(bucket, 0) + 1
            lab_buckets = by_lab.setdefault(lab, dict.fromkeys(ORDER_BUCKETS, 0))
            if bucket in lab_buckets:
                lab_buckets[bucket] += 1

        return {
            "total": len(rows),
            "by_bucket": by_bucket,
            "by_lab": [
                {"lab_code": lab, "by_bucket": buckets} for lab, buckets in sorted(by_lab.items())
            ],
        }


async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardService:
    return DashboardService(session)
