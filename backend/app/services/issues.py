from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.common.enums import NotificationChannel
from app.common.recipients import recipients_for_role_in_lab
from app.core.database import get_db
from app.db.models.issues import Issue
from app.repos.issues import IssueRepository
from app.schemas.issues import IssueCreate, IssueListParams, IssueUpdate
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)

# How long to wait before the first escalation kicks in. Hard-coded short for
# demo / development ergonomics; the production default + per-severity tuning
# will move to ``system_settings.alertRules`` once that module exists.
INITIAL_ESCALATION_DELAY = timedelta(seconds=10)


class IssueService:
    """Issue use-cases. Wraps IssueRepository and owns the commit boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = IssueRepository(session)

    async def create_issue(self, payload: IssueCreate, user: CurrentUser) -> Issue:
        # Pass next_escalation_time so it lands in the INSERT — setting it
        # post-flush triggers a second UPDATE which expires updated_at via
        # the server-side onupdate trigger and breaks downstream serialization
        # under async (MissingGreenlet).
        issue = await self._repo.create_issue(
            payload,
            next_escalation_time=datetime.now(UTC) + INITIAL_ESCALATION_DELAY,
        )
        await self._session.commit()

        # Level-0 initial fan-out: engineers are first responders. If they
        # don't close the issue within INITIAL_ESCALATION_DELAY, the Celery
        # worker bumps to level 1 and notifies the lab supervisor.
        # Notification is best-effort: a failure here must not fail the
        # whole create — the issue is already persisted.
        try:
            notification_service = NotificationService(self._session)
            engineer_ids = await recipients_for_role_in_lab(
                self._session, lab_id=issue.lab_id, role_name="lab_engineer"
            )
            if engineer_ids:
                await notification_service.notify(
                    recipient_ids=engineer_ids,
                    lab_id=issue.lab_id,
                    source_type="issue",
                    source_id=str(issue.id),
                    title=f"[新異常] {issue.title}",
                    body=issue.description,
                    severity=issue.severity,
                    channels=[NotificationChannel.IN_APP],
                )
        except Exception:
            logger.exception("initial-notify failed for issue=%s", issue.id)

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

    async def list_acknowledgements(
        self, issue_id: UUID, user: CurrentUser
    ) -> list[dict[str, Any]]:
        """Who has read a notification about this issue.

        Calls ``get_issue`` first so the lab-scope filter applies — callers
        who can't see the issue get a 404 here too, not an empty list.
        """
        await self._repo.get_issue(issue_id, user)  # raises NotFoundError if out of scope
        return await self._repo.list_acknowledgements(issue_id)


async def get_issue_service(session: Annotated[AsyncSession, Depends(get_db)]) -> IssueService:
    return IssueService(session)
