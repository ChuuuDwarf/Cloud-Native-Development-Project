from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.common.dependencies.scope import apply_lab_scope
from app.common.enums import NotificationStatus
from app.common.errors import NotFoundError
from app.db.models.issues import Issue
from app.db.models.notifications import Notification
from app.db.models.roles import Role
from app.db.models.users import User
from app.schemas.issues import IssueCreate, IssueListParams, IssueUpdate


class IssueRepository:
    """Async CRUD for issues, scoped by lab via apply_lab_scope."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_issue(
        self,
        payload: IssueCreate,
        *,
        next_escalation_time: datetime | None = None,
    ) -> Issue:
        issue = Issue(**payload.model_dump())
        # next_escalation_time isn't on IssueCreate (it's a server-controlled
        # field), but callers — currently IssueService — pass it in so the
        # initial escalation deadline lands in the same INSERT.
        if next_escalation_time is not None:
            issue.next_escalation_time = next_escalation_time
        self.session.add(issue)
        await self.session.flush()
        await self.session.refresh(issue)

        return issue

    async def get_issue(self, issue_id: UUID, user: CurrentUser) -> Issue:
        stmt = select(Issue).where(Issue.id == issue_id)
        stmt = apply_lab_scope(stmt, user, Issue.lab_id)
        result = await self.session.execute(stmt)
        issue = result.scalar_one_or_none()

        if issue is None:
            raise NotFoundError(f"Issue {issue_id} not found")

        return issue

    async def list_issues(
        self, params: IssueListParams, user: CurrentUser
    ) -> tuple[list[Issue], int]:
        stmt = select(Issue)

        stmt = apply_lab_scope(stmt, user, Issue.lab_id)

        if params.status is not None:
            stmt = stmt.where(Issue.status == params.status)
        if params.severity is not None:
            stmt = stmt.where(Issue.severity == params.severity)
        if params.type is not None:
            stmt = stmt.where(Issue.type == params.type)
        if params.assigned_to is not None:
            stmt = stmt.where(Issue.assigned_to == params.assigned_to)
        if params.target_type is not None:
            stmt = stmt.where(Issue.target_type == params.target_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(Issue.created_at.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def list_acknowledgements(self, issue_id: UUID) -> list[dict[str, Any]]:
        """All users who have marked a notification for this issue as read.

        Returns one row per (user, channel) read event. Sorted by read_at
        ascending so the "first acknowledger" is on top.

        Implementation note: the User→Role join via ``user_roles`` would
        produce one row per role per acknowledgement, double-counting users
        who hold multiple roles. We dedupe in Python by ``(user_id, channel,
        read_at)`` and keep the first role we see — sufficient for the UI's
        "primary role" display. If the team ever needs full role lists,
        switch to ``string_agg`` + GROUP BY.
        """
        stmt = (
            select(
                User.id.label("user_id"),
                User.name.label("user_name"),
                User.email.label("user_email"),
                Role.name.label("role"),
                Notification.channel.label("channel"),
                Notification.read_at.label("read_at"),
            )
            .select_from(Notification)
            .join(User, User.id == Notification.recipient_id)
            .outerjoin(User.roles)
            .where(
                Notification.source_type == "issue",
                Notification.source_id == str(issue_id),
                Notification.status == NotificationStatus.READ,
                Notification.read_at.is_not(None),
            )
            .order_by(Notification.read_at.asc())
        )
        result = await self.session.execute(stmt)
        seen: dict[tuple[UUID, str, datetime], dict[str, Any]] = {}
        for row in result.all():
            key = (row.user_id, row.channel, row.read_at)
            if key not in seen:
                seen[key] = dict(row._mapping)
        return list(seen.values())

    async def update_issue(self, issue_id: UUID, payload: IssueUpdate, user: CurrentUser) -> Issue:
        issue = await self.get_issue(issue_id, user)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(issue, field, value)

        await self.session.flush()
        await self.session.refresh(issue)

        return issue
