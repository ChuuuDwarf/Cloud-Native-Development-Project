"""HTTP routes for /api/notifications.

Three endpoints, all gated by ``notifications:read``:

- ``GET /api/notifications`` — list the caller's notifications.
- ``GET /api/notifications/{id}`` — fetch one.
- ``POST /api/notifications/actions`` — batch mark-as-read.

Notifications are never user-created via REST (see
``app/services/notifications.py``'s ``notify()`` for the internal pipeline),
and they are not deleted or updatable beyond the read flag. The action
endpoint takes a ``MarkReadPayload`` and returns a ``MarkReadResult``.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.common.dependencies import (
    CurrentUser,
    PaginationParams,
    get_pagination,
    require_permission,
)
from app.common.enums import NotificationChannel, NotificationStatus, Severity
from app.common.schemas import ApiResponse, PageResponse
from app.schemas.notifications import (
    ListNotificationsQuery,
    MarkReadPayload,
    MarkReadResult,
    NotificationRead,
)
from app.services.notifications import NotificationService, get_notification_service

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=PageResponse[NotificationRead])
async def list_notifications(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    user: Annotated[CurrentUser, Depends(require_permission("notifications:read"))],
    status_filter: NotificationStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = Query(default=None),
    channel: NotificationChannel | None = Query(default=None),
    source_type: str | None = Query(default=None, alias="sourceType"),
) -> PageResponse[NotificationRead]:
    params = ListNotificationsQuery(
        status=status_filter,
        severity=severity,
        channel=channel,
        sourceType=source_type,
        page=pagination.page,
        pageSize=pagination.page_size,
    )
    items, total = await service.list_notifications(params, user)
    return PageResponse[NotificationRead](
        items=[NotificationRead.model_validate(n) for n in items],
        page=pagination.page,
        pageSize=pagination.page_size,
        total=total,
    )


@router.get("/{notification_id}", response_model=ApiResponse[NotificationRead])
async def get_notification(
    notification_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    user: Annotated[CurrentUser, Depends(require_permission("notifications:read"))],
) -> ApiResponse[NotificationRead]:
    notification = await service.get_notification(notification_id, user)
    return ApiResponse(data=NotificationRead.model_validate(notification))


@router.post("/actions", response_model=ApiResponse[MarkReadResult])
async def mark_notifications_read(
    payload: MarkReadPayload,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    user: Annotated[CurrentUser, Depends(require_permission("notifications:read"))],
) -> ApiResponse[MarkReadResult]:
    marked_count, skipped_ids = await service.mark_read(payload.ids, user)
    result = MarkReadResult(markedCount=marked_count, skippedIds=skipped_ids)
    return ApiResponse(data=result, message="marked")
