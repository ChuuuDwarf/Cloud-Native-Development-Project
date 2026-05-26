from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.core.database import get_db
from app.db.models.issues import Issue
from app.repos.issues import IssueRepository
from app.schemas.issues import IssueCreate, IssueListParams, IssueUpdate


class IssueService:
    """Issue use-cases. Wraps IssueRepository and owns the commit boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = IssueRepository(session)

    async def create_issue(self, payload: IssueCreate, user: CurrentUser) -> Issue:
        issue = await self._repo.create_issue(payload)
        await self._session.commit()
        return issue

    async def get_issue(self, issue_id: UUID, user: CurrentUser) -> Issue:
        return await self._repo.get_issue(issue_id, user)

    async def list_issues(
        self, params: IssueListParams, user: CurrentUser
    ) -> tuple[list[Issue], int]:
        return await self._repo.list_issues(params, user)

    async def update_issue(self, issue_id: UUID, payload: IssueUpdate, user: CurrentUser) -> Issue:
        issue = await self._repo.update_issue(issue_id, payload, user)
        await self._session.commit()
        return issue


async def get_issue_service(session: Annotated[AsyncSession, Depends(get_db)]) -> IssueService:
    return IssueService(session)
