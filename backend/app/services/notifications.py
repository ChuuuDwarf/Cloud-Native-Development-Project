"""Notifications service.

The public API surface for *consumers* (FastAPI routes) is just three
methods: list, get, mark_read. The fourth method, :meth:`notify`, is the
internal fan-out helper called by *other services* (issue escalation,
order approval, etc.) to dispatch notifications across recipients x channels.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.common.enums import IssueStatus, NotificationChannel, NotificationStatus, Severity
from app.core.database import get_db
from app.db.models.issues import Issue
from app.db.models.notifications import Notification
from app.db.models.users import User
from app.repos.notifications import NotificationRepository
from app.schemas.notifications import ListNotificationsQuery

logger = logging.getLogger(__name__)


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

        # PHONE channel: fan out via Celery so the worker handles the
        # blocking HTTP call to the CHT TAS API. We only enqueue if at
        # least one row used PHONE — otherwise no DB lookup for phones.
        if NotificationChannel.PHONE in effective_channels:
            await self._dispatch_phone_callout(
                recipient_ids=unique_recipients,
                title=title,
                body=body,
                source_id=source_id,
            )
        return rows

    async def _dispatch_phone_callout(
        self,
        *,
        recipient_ids: list[UUID],
        title: str,
        body: str,
        source_id: str,
    ) -> None:
        """Look up recipients' phones and enqueue ``send_callout`` once.

        Best-effort: a missing phone, an empty result set, or a Celery /
        broker hiccup must not break the original notification flow — log
        and move on. The in-app channel still carries the message.
        """
        try:
            stmt = select(User.phone).where(User.id.in_(recipient_ids), User.phone.is_not(None))
            result = await self._session.execute(stmt)
            phones = [row[0] for row in result.all() if row[0]]
            if not phones:
                logger.info(
                    "phone callout skipped for source=%s: no recipient phones",
                    source_id,
                )
                return

            # Lazy import to avoid Celery being imported at FastAPI startup
            # (also keeps the worker module out of the request-cycle import graph).
            from app.workers.phone_sender import send_callout

            send_callout.delay(
                phones=phones,
                title=title,
                body=body,
                tags=[f"issue:{source_id}"],
            )
            logger.info(
                "phone callout enqueued for source=%s phones=%d",
                source_id,
                len(phones),
            )
        except Exception:
            logger.exception("phone callout dispatch failed for source=%s", source_id)

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
        """Mark notifications as read AND acknowledge their source issues.

        Side effect: any of the just-flipped notifications whose
        ``source_type == "issue"`` triggers an ack on the corresponding
        Issue row — ``next_escalation_time`` is cleared so the Beat worker
        stops escalating, and ``handled_at`` is stamped the first time
        (subsequent reads don't overwrite).

        Both happen in the same transaction so a recipient marking
        their alert read is the canonical "I see this, stop paging
        people" signal. Phone-pickup-as-ack would need the CHT TAS
        MQTT callback wired up (out of scope).
        """
        marked_count, skipped = await self._repo.mark_read(notification_ids, user)
        if marked_count > 0:
            await self._ack_source_issues(notification_ids, user)
        await self._session.commit()
        return marked_count, skipped

    async def _ack_source_issues(
        self,
        notification_ids: list[UUID],
        user: CurrentUser,
    ) -> None:
        """Stop escalation for any issue whose notification was just read.

        Reads back from the same session (the repo's UPDATE...RETURNING
        already flipped the rows but hasn't committed). For each unique
        ``source_id`` where ``source_type == "issue"``, set the Issue's
        ``next_escalation_time`` to NULL and ``handled_at`` to now
        (coalesce so we keep the first ack timestamp).
        """
        if not notification_ids:
            return

        source_id_stmt = (
            select(Notification.source_id)
            .where(
                Notification.id.in_(notification_ids),
                Notification.recipient_id == user.id,
                Notification.source_type == "issue",
                Notification.status == NotificationStatus.READ,
            )
            .distinct()
        )
        source_ids = list((await self._session.execute(source_id_stmt)).scalars().all())
        if not source_ids:
            return

        # Notification.source_id is String (polymorphic across resource
        # types); Issue.id is UUID. Convert defensively — a stray
        # non-UUID source_id from a bad notify() call shouldn't 500 the
        # whole mark-read.
        try:
            issue_ids = [UUID(s) for s in source_ids]
        except (TypeError, ValueError):
            logger.exception("non-uuid source_id in notification batch: %s", source_ids)
            return

        now = datetime.now(UTC)
        ack_stmt = (
            update(Issue)
            # Skip CLOSED so a stray read on a fully-resolved issue doesn't
            # downgrade its status back to ACKNOWLEDGED.
            .where(Issue.id.in_(issue_ids), Issue.status != IssueStatus.CLOSED)
            .values(
                status=IssueStatus.ACKNOWLEDGED,
                next_escalation_time=None,
                handled_at=func.coalesce(Issue.handled_at, now),
            )
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(ack_stmt)

        logger.info(
            "acked %d issue(s) via notification read by user=%s",
            len(issue_ids),
            user.id,
        )


async def get_notification_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationService:
    return NotificationService(session)
