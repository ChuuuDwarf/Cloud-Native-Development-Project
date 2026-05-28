"""Round-trip publish/subscribe test for the dashboard SSE channels.

This test exists specifically to guard the channel-keying contract:
publishers post to ``dashboard:events:{lab_code}`` and the SSE handler
subscribes to ``dashboard:events:{user.lab_code}``. If anyone re-introduces
the old ``Lab.name`` (display name) keying — or otherwise lets the
publisher and subscriber drift — this round-trip test fails fast.

Skipped automatically when Redis is unavailable (CI without a Redis
sidecar will skip rather than fail).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from typing import cast

import pytest
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.modules.dashboard import publisher as publisher_module
from app.modules.dashboard.publisher import (
    _GLOBAL_CHANNEL,
    _lab_channel,
    listen,
    publish_new_escalation,
)


async def _redis_available() -> bool:
    """Probe the configured Redis. Returns False on any connection error so
    the test environment can skip cleanly when Redis isn't running.
    """
    client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        return bool(await client.ping())
    except Exception:
        return False
    finally:
        await client.aclose()


@pytest.fixture(autouse=True)
async def _require_redis() -> None:
    if not await _redis_available():
        pytest.skip("Redis not available in this environment")
    # The publisher module memoises its aioredis client at module scope.
    # pytest-asyncio gives each test its own event loop, so a client bound
    # to a previous test's loop is dead by the time this test starts and
    # will raise ``Event loop is closed`` on cleanup. Reset between tests.
    if publisher_module._redis is not None:
        # The old loop may already be gone — best effort cleanup.
        with contextlib.suppress(Exception):
            await publisher_module._redis.aclose()
        publisher_module._redis = None


async def test_publish_per_lab_event_reaches_lab_supervisor_subscriber() -> None:
    """A subscriber on global + a specific lab channel receives exactly one
    event when the publisher posts to that lab — proves channel keys match.
    """
    lab_code = "LAB-RT-TEST"
    received: list[str] = []

    # listen() is annotated as AsyncIterator[str] but is implemented as an
    # async generator, so we cast to AsyncGenerator to call aclose() — the
    # cleanest way to drain the pubsub subscription deterministically.
    gen = cast(
        "AsyncGenerator[str, None]",
        listen(channels=[_GLOBAL_CHANNEL, _lab_channel(lab_code)]),
    )

    async def consume() -> None:
        async for ev in gen:
            received.append(ev)
            break  # one event is all we need
        # Explicitly close so listen()'s finally block (unsubscribe + close
        # the pubsub) runs while this test's loop is still alive.
        await gen.aclose()

    task = asyncio.create_task(consume())
    # Give the subscriber a moment to land on Redis before we publish,
    # otherwise the publish can race the SUBSCRIBE and the message vanishes.
    await asyncio.sleep(0.1)

    await publish_new_escalation(lab_code)

    try:
        await asyncio.wait_for(task, timeout=2.0)
    except TimeoutError:
        task.cancel()
        raise AssertionError(
            "subscriber timed out — publisher/subscriber channel keys drifted?"
        ) from None

    assert received == ["new_escalation"]


async def test_cross_lab_viewer_pattern_subscription_receives_per_lab_event() -> None:
    """A psubscriber on ``dashboard:events:*`` (the system_admin /
    general_supervisor wiring) picks up per-lab publishes without enumerating
    each lab channel.
    """
    lab_code = "LAB-RT-WILDCARD"
    received: list[str] = []

    gen = cast(
        "AsyncGenerator[str, None]",
        listen(channels=[], patterns=["dashboard:events:*"]),
    )

    async def consume() -> None:
        async for ev in gen:
            received.append(ev)
            break
        await gen.aclose()

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.1)

    await publish_new_escalation(lab_code)

    try:
        await asyncio.wait_for(task, timeout=2.0)
    except TimeoutError:
        task.cancel()
        raise AssertionError(
            "psubscriber timed out — wildcard pattern not matching per-lab channels?"
        ) from None

    assert received == ["new_escalation"]
