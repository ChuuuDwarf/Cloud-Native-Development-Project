"""Redis pub/sub helpers for dashboard SSE invalidation.

Other modules (workers, orders, reports) call these helpers on important
state changes; the dashboard SSE handler subscribes to the matching channels
and forwards the event name (no payload) so the frontend can
``queryClient.invalidateQueries(["dashboard"])`` and re-fetch.

Channels:

* ``dashboard:events:global`` — every event is also published here for
  general_supervisor / system_admin who watch the whole plant.
* ``dashboard:events:{lab_code}`` — per-lab fanout so a lab_supervisor only
  receives invalidations relevant to their own lab. ``lab_code`` is the
  ASCII lab identifier (e.g. ``LAB-A``), **not** the display name (e.g.
  ``電性測試實驗室``). The SSE handler keys its subscription off
  ``CurrentUser.lab_code``; publishers must translate any lab display name
  back to a code before calling these helpers, otherwise lab_supervisor
  channels will silently never match.

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


def _lab_channel(lab_code: str | None) -> str:
    """Return the per-lab channel for ``lab_code`` (ASCII, e.g. ``LAB-A``).

    Falls back to the global channel when ``lab_code`` is ``None``.
    """
    return f"dashboard:events:{lab_code}" if lab_code else _GLOBAL_CHANNEL


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


async def publish_new_escalation(lab_code: str | None) -> None:
    """Called from the escalation worker after an issue is bumped a level.

    ``lab_code`` is the ASCII lab identifier (``Lab.code``, e.g. ``LAB-A``),
    **not** the display name. If given, the event lands on the per-lab
    channel only — cross-lab viewers (general_supervisor / system_admin)
    pick it up via ``dashboard:events:*`` (PSUBSCRIBE), so a separate global
    publish would double-deliver to lab_supervisor (who subscribes to both
    global and their own lab). Pass ``None`` for truly global events.
    """
    await _publish(_lab_channel(lab_code), "new_escalation")


async def publish_new_pending_approval(lab_code: str | None) -> None:
    """Called from order service when an order transitions to pending_approval.

    See :func:`publish_new_escalation` for ``lab_code`` semantics and
    channel-selection rationale.
    """
    await _publish(_lab_channel(lab_code), "new_pending_approval")


async def publish_report_returned(lab_code: str | None) -> None:
    """Called from reports service when a report transitions to RETURNED.

    See :func:`publish_new_escalation` for ``lab_code`` semantics and
    channel-selection rationale.
    """
    await _publish(_lab_channel(lab_code), "report_returned")


async def listen(channels: list[str], *, patterns: list[str] | None = None) -> AsyncIterator[str]:
    """Async-generator yielding event names as they arrive on any of
    ``channels`` or matching any of ``patterns`` (Redis PSUBSCRIBE globs).

    Caller (the SSE handler) must consume via ``async for``. We clean up the
    pubsub subscription in the ``finally`` block to avoid leaking the
    Redis pubsub connection across requests.

    Patterns are typically used by cross-lab viewers (general_supervisor /
    system_admin) to subscribe to ``dashboard:events:*`` without enumerating
    every lab. Per-channel ``message`` events and per-pattern ``pmessage``
    events are both surfaced.
    """
    patterns = patterns or []
    pubsub = _get_redis().pubsub()
    if channels:
        await pubsub.subscribe(*channels)
    if patterns:
        await pubsub.psubscribe(*patterns)
    try:
        async for message in pubsub.listen():
            mtype = message.get("type")
            if mtype not in ("message", "pmessage"):
                continue
            yield message.get("data") or ""
    finally:
        if channels:
            await pubsub.unsubscribe(*channels)
        if patterns:
            await pubsub.punsubscribe(*patterns)
        await pubsub.aclose()
