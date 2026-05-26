"""Pydantic schemas for the notifications module.

Notifications are *not* user-creatable via REST — they are produced by
``NotificationService.notify()`` from inside other services (e.g. issue
escalation). The API surface exposed here covers list / read / mark-read
only. Wire format is camelCase per ``docs/integration_contract.md`` §6.1.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.enums import NotificationChannel, NotificationStatus, Severity


class NotificationRead(BaseModel):
    """Response body for ``GET /api/notifications/{id}`` and list items.

    ``recipient_id`` always equals the authenticated caller under normal
    scope; exposed for debugging and to keep the schema stable for future
    admin / impersonation views.
    """

    id: UUID
    recipient_id: UUID = Field(alias="recipientId")
    lab_id: UUID = Field(alias="labId")

    # source_type is intentionally a free-form string (not an enum): notifications
    # can fan out from heterogeneous sources (issues / orders / wips / ...) whose
    # id-encoding differs (UUID vs ints vs human codes), so source_id is also str.
    source_type: str = Field(alias="sourceType")
    source_id: str = Field(alias="sourceId")

    title: str
    body: str
    severity: Severity
    channel: NotificationChannel

    status: NotificationStatus
    read_at: datetime | None = Field(alias="readAt")

    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class ListNotificationsQuery(BaseModel):
    """Query parameters for ``GET /api/notifications``.

    The scope filter (only show notifications where ``recipient_id`` equals
    the authenticated caller) is applied in the service from the auth
    context, not as a query param — callers cannot list other users'
    notifications.
    """

    status: NotificationStatus | None = Field(default=None)
    severity: Severity | None = Field(default=None)
    channel: NotificationChannel | None = Field(default=None)
    source_type: str | None = Field(default=None, alias="sourceType")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")

    model_config = {"populate_by_name": True}


class MarkReadPayload(BaseModel):
    """Request body for ``POST /api/notifications/actions``.

    Batch mark-as-read: caller supplies the notification ids they want
    to flip from ``unread`` to ``read``. Service silently ignores ids
    that aren't visible to the caller (scope filter) — no per-id 404,
    so partial calls don't leak existence of others' notifications.
    """

    ids: list[UUID] = Field(min_length=1, max_length=100)


class MarkReadResult(BaseModel):
    """Response body for ``POST /api/notifications/actions``.

    ``marked_count`` is the number of notifications that flipped to read in
    this call. ``skipped_ids`` lists ids that were either invisible (scope
    filtered) or already read — caller can use this to reconcile UI state.
    """

    marked_count: int = Field(alias="markedCount")
    skipped_ids: list[UUID] = Field(alias="skippedIds")

    model_config = {"populate_by_name": True}
