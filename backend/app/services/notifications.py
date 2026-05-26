"""Notifications service.

The public API surface for *consumers* (FastAPI routes) is just three
methods: list, get, mark_read. The fourth method, :meth:`notify`, is the
internal fan-out helper called by *other services* (issue escalation,
order approval, etc.) to dispatch notifications across recipients x channels.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.common.enums import NotificationChannel, Severity
from app.core.database import get_db
from app.db.models.notifications import Notification
from app.repos.notifications import NotificationRepository
from app.schemas.notifications import ListNotificationsQuery


class NotificationService:
    """Notification use-cases. Wraps NotificationRepository, owns commits."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificationRepository(session)

    async def notify(
        self,
        *,
        recipient_ids: list[UUID],
        lab_id: UUID,
        source_type: str,
        source_id: str,
        title: str,
        body: str = "",
        severity: Severity = Severity.MEDIUM,
        channels: list[NotificationChannel] | None = None,
    ) -> list[Notification]:
        """Fan out a single event into per-(recipient x channel) rows.

        Produces ``len(unique_recipients) * len(channels)`` notification
        rows and commits them atomically. Returns the inserted rows so the
        caller can publish SSE / dispatch email tasks.

        Duplicate ``recipient_ids`` are collapsed (preserving first-seen
        order) so accidental unions of "assignees + watchers" don't create
        duplicate notifications. Empty ``recipient_ids`` is a no-op and
        returns ``[]`` without opening a transaction. ``channels`` defaults
        to in-app only.

        This method owns its commit. Callers that need the notification
        rows to participate in their own transaction should use
        :class:`NotificationRepository` directly instead.
        """
        if not recipient_ids:
            return []

        effective_channels = channels or [NotificationChannel.IN_APP]
        unique_recipients = list(dict.fromkeys(recipient_ids))

        rows = [
            Notification(
                recipient_id=recipient_id,
                lab_id=lab_id,
                source_type=source_type,
                source_id=source_id,
                title=title,
                body=body,
                severity=severity,
                channel=channel,
            )
            for recipient_id in unique_recipients
            for channel in effective_channels
        ]

        self._session.add_all(rows)
        await self._session.flush()
        await self._session.commit()
        return rows

    async def get_notification(self, notification_id: UUID, user: CurrentUser) -> Notification:
        return await self._repo.get_notification(notification_id, user)

    async def list_notifications(
        self,
        params: ListNotificationsQuery,
        user: CurrentUser,
    ) -> tuple[list[Notification], int]:
        return await self._repo.list_notifications(params, user)

    async def mark_read(
        self,
        notification_ids: list[UUID],
        user: CurrentUser,
    ) -> tuple[int, list[UUID]]:
        result = await self._repo.mark_read(notification_ids, user)
        await self._session.commit()
        return result


async def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationService:
    return NotificationService(session)
