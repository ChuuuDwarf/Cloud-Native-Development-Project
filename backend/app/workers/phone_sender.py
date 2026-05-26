"""Celery task: fire a CHT TAS phone callout.

Enqueued by ``NotificationService.notify`` whenever a notification's channel
is ``NotificationChannel.PHONE``. Runs in the Celery worker (sync) so it can
use the sync :class:`app.services.cht_tas.CHTTASClient` directly.

Graceful degradation: if the TAS client isn't configured (no API key /
service number in env), the task logs the would-be call and returns — so
dev environments can exercise the escalation pipeline without making real
calls. A real production deployment sets both env vars and gets real calls.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.celery_app import celery_app
from app.services.cht_tas import CHTTASClient, CHTTASError

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.workers.phone_sender.send_callout",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def send_callout(
    self: Any,
    *,
    phones: list[str],
    title: str,
    body: str,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Make a callout to each phone in ``phones``.

    ``title`` becomes the welcome text, ``body`` the main text. We keep it
    short to fit TAS's 200-char text cap (CJK chars count as 1).
    """
    if not phones:
        logger.warning("phone_sender skipped: no recipients")
        return {"status": "skipped", "reason": "no recipients"}

    client = CHTTASClient()
    if not client.configured:
        logger.warning(
            "phone_sender skipped: CHT client not configured. would have called "
            "phones=%s title=%r body=%r",
            phones,
            title,
            body,
        )
        return {"status": "skipped", "reason": "not configured"}

    # Trim text to be safe under TAS's 200-char cap. Keep the title in the
    # welcome slot so callers always hear what kind of alert it is even if
    # body is truncated.
    short_text = body if len(body) <= 180 else body[:177] + "..."

    try:
        return client.callout(
            phones=phones,
            text=short_text,
            welcome_text=title[:180],
            tags=tags,
        )
    except CHTTASError as exc:
        logger.exception("CHT callout failed; retrying")
        raise self.retry(exc=exc) from exc
