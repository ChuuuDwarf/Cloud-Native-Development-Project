from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.common.dependencies.scope import apply_lab_scope
from app.common.errors import NotFoundError
from app.db.models.issues import Issue
from app.schemas.issues import IssueCreate, IssueListParams, IssueUpdate


class IssueRepository:
    """Async CRUD for issues, scoped by lab via apply_lab_scope."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_issue(self, payload: IssueCreate) -> Issue:
        issue = Issue(**payload.model_dump())
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

    async def update_issue(self, issue_id: UUID, payload: IssueUpdate, user: CurrentUser) -> Issue:
        issue = await self.get_issue(issue_id, user)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(issue, field, value)

        await self.session.flush()
        await self.session.refresh(issue)

        return issue
