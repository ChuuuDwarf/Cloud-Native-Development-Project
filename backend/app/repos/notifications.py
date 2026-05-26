"""Notification repository — async CRUD + recipient-scoped queries.

Unlike ``app/repos/issues.py`` which uses :func:`apply_lab_scope`, this
module enforces a stricter rule: callers can only see notifications where
``recipient_id == user.id``. Admins do not bypass this — admin-as-user
inspection is a separate endpoint to be designed when needed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.common.enums import NotificationStatus
from app.common.errors import NotFoundError
from app.db.models.notifications import Notification
from app.schemas.notifications import ListNotificationsQuery


class NotificationRepository:
    """Async CRUD for notifications, scoped to the authenticated recipient."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_notification(self, notification: Notification) -> Notification:
        """Insert a pre-built Notification.

        Caller is expected to construct the ORM object (typically
        ``NotificationService.notify()``), since notification production is
        an internal pipeline and there is no user-facing create DTO.
        """
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def get_notification(self, notification_id: UUID, user: CurrentUser) -> Notification:
        """Fetch a single notification visible to ``user``.

        A 404 is raised for both "id doesn't exist" and "id belongs to
        another recipient", so callers cannot use this endpoint to probe
        the existence of other users' notifications.
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == user.id,
        )
        result = await self.session.execute(stmt)
        notification = result.scalar_one_or_none()

        if notification is None:
            raise NotFoundError(f"Notification {notification_id} not found")

        return notification

    async def list_notifications(
        self,
        params: ListNotificationsQuery,
        user: CurrentUser,
    ) -> tuple[list[Notification], int]:
        """List ``user``'s notifications, newest first, with optional filters.

        Recipient scope is hard-coded: even system_admin only sees their own
        notifications via this method. Use a dedicated admin endpoint when
        cross-recipient visibility is needed.
        """
        stmt = select(Notification).where(Notification.recipient_id == user.id)

        if params.status is not None:
            stmt = stmt.where(Notification.status == params.status)
        if params.severity is not None:
            stmt = stmt.where(Notification.severity == params.severity)
        if params.channel is not None:
            stmt = stmt.where(Notification.channel == params.channel)
        if params.source_type is not None:
            stmt = stmt.where(Notification.source_type == params.source_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(Notification.created_at.desc())
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def mark_read(
        self,
        notification_ids: list[UUID],
        user: CurrentUser,
    ) -> tuple[int, list[UUID]]:
        """Batch flip ``unread`` → ``read`` for visible+unread ids.

        Returns ``(marked_count, skipped_ids)``:
        - ``marked_count``: how many rows actually flipped.
        - ``skipped_ids``: ids the caller asked about that were either
          invisible (wrong recipient) or already read. The two cases are
          deliberately conflated so callers can't infer existence of other
          users' notifications.
        """
        if not notification_ids:
            return 0, []

        now = datetime.now(UTC)

        stmt = (
            update(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.recipient_id == user.id,
                Notification.status == NotificationStatus.UNREAD,
            )
            .values(status=NotificationStatus.READ, read_at=now)
            .returning(Notification.id)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.session.execute(stmt)
        flipped_ids = set(result.scalars().all())

        skipped = [nid for nid in notification_ids if nid not in flipped_ids]
        return len(flipped_ids), skipped
