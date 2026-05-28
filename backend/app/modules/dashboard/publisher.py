"""Redis pub/sub helpers for dashboard SSE invalidation.

Other modules (workers, orders, reports) call these helpers on important
state changes; the dashboard SSE handler subscribes to the matching channels
and forwards the event name (no payload) so the frontend can
``queryClient.invalidateQueries(["dashboard"])`` and re-fetch.

Channels:

* ``dashboard:events:global`` — every event is also published here for
  general_supervisor / system_admin who watch the whole plant.
* ``dashboard:events:{lab_code}`` — per-lab fanout so a lab_supervisor only
  receives invalidations relevant to their own lab.

All publishes are best-effort: failures are logged and swallowed so a Redis
outage doesn't take down the writer.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_GLOBAL_CHANNEL = "dashboard:events:global"


def _lab_channel(lab_name: str | None) -> str:
    return f"dashboard:events:{lab_name}" if lab_name else _GLOBAL_CHANNEL


_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    """Lazy singleton — avoid opening a connection at import time so unit
    tests that don't need Redis can import this module freely.
    """
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def _publish(channel: str, event: str) -> None:
    """Publish ``event`` (event name only, no payload) to ``channel``."""
    try:
        await _get_redis().publish(channel, event)
    except Exception:
        logger.exception("dashboard publish failed channel=%s event=%s", channel, event)


async def publish_new_escalation(lab_name: str | None) -> None:
    """Called from the escalation worker after an issue is bumped a level."""
    await _publish(_lab_channel(lab_name), "new_escalation")
    if lab_name:
        await _publish(_GLOBAL_CHANNEL, "new_escalation")


async def publish_new_pending_approval(lab_name: str | None) -> None:
    """Called from order service when an order transitions to pending_approval."""
    await _publish(_lab_channel(lab_name), "new_pending_approval")
    if lab_name:
        await _publish(_GLOBAL_CHANNEL, "new_pending_approval")


async def publish_report_returned(lab_name: str | None) -> None:
    """Called from reports service when a report transitions to RETURNED."""
    await _publish(_lab_channel(lab_name), "report_returned")
    if lab_name:
        await _publish(_GLOBAL_CHANNEL, "report_returned")


async def listen(channels: list[str]) -> AsyncIterator[str]:
    """Async-generator yielding event names as they arrive on any of
    ``channels``.

    Caller (the SSE handler) must consume via ``async for``. We clean up the
    pubsub subscription in the ``finally`` block to avoid leaking the
    Redis pubsub connection across requests.
    """
    pubsub = _get_redis().pubsub()
    await pubsub.subscribe(*channels)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            yield message.get("data") or ""
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.aclose()
