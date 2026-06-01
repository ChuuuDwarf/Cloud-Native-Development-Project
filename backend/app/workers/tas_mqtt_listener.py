"""TAS MQTT listener — turn a phone pickup into an issue acknowledgement.

Subscribes to ``phone-conn/calloutResult/${TAS_SN_KEY}`` and reacts to
``status == "answered"`` events. The original REST callout (fired by
``NotificationService.notify`` via ``app.workers.phone_sender.send_callout``)
embeds the source notification's correlation id in the ``tags`` array as
``"issue:<UUID>"``; TAS echoes the first tag back on each MQTT message.
We parse that tag, resolve the issue, and run the same ack path the in-app
``mark_read`` flow uses — flipping the unread PHONE notification rows to
READ and clearing ``next_escalation_time`` on the issue so the Celery
escalation loop stops paging people.

This is a separate long-running process, not a Celery task. ``main()``
constructs a paho client, attaches reconnect / SIGTERM handlers, and loops
forever. Run with::

    python -m app.workers.tas_mqtt_listener

``TAS_ENABLED=False`` makes ``main()`` log + exit 0 immediately so docker
containers in CI / local dev don't crash-loop without credentials.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import ssl
import sys
from types import FrameType
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

# paho-mqtt is intentionally imported lazily / behind a try-except so that
# unit tests can monkeypatch the module without forcing the dependency to be
# installed in every environment. Production deployments pin it in
# requirements.txt.
try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - exercised only when dep missing
    mqtt = None  # type: ignore[assignment]

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)

# Topic templates — keep these in one place so a sn_key swap doesn't touch
# both the subscribe call and any logging helper.
CALLOUT_RESULT_TOPIC = "phone-conn/calloutResult/{sn_key}"
CALL_EVENT_TOPIC = "phone-conn/callEvent/{sn_key}"
ISSUE_TAG_PREFIX = "issue:"


def _parse_issue_id(tag_value: Any) -> UUID | None:
    """Extract a UUID from a TAS ``tag`` field.

    TAS returns ``tag`` as a *string* per the spec, but the originating
    REST request sends ``tags`` as an array — older sample code suggests
    some deployments echo the whole array back. Accept either shape to
    avoid brittle parsing.
    """
    if tag_value is None:
        return None
    raw = tag_value[0] if isinstance(tag_value, list) and tag_value else tag_value
    if not isinstance(raw, str) or not raw.startswith(ISSUE_TAG_PREFIX):
        return None
    try:
        return UUID(raw[len(ISSUE_TAG_PREFIX) :])
    except ValueError:
        return None


async def _ack_issue_async(issue_id: UUID) -> int:
    """Open a fresh async session and ack the issue.

    The listener is a long-running sync process; each MQTT message gets its
    own short-lived NullPool engine so connections never cross event loops.
    Mirrors the per-task engine pattern in ``app.workers.experiment_tasks``.
    """
    engine: AsyncEngine = create_async_engine(
        get_settings().database_url, poolclass=NullPool, future=True
    )
    session_local = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession, autoflush=False
    )
    try:
        async with session_local() as session:
            service = NotificationService(session)
            return await service.mark_notification_answered(issue_id)
    finally:
        await engine.dispose()


def handle_message_payload(payload: dict[str, Any]) -> int | None:
    """Process one parsed JSON message body.

    Pulled out of the paho callback so unit tests can drive it directly
    without setting up an MQTT client. Returns the number of notification
    rows flipped, or ``None`` if the message was ignored (wrong status,
    no tag, malformed tag).
    """
    status = payload.get("status")
    if status != "answered":
        # Only ``answered`` counts as acknowledgement per the product call.
        # Other terminal states (reject/busy/timeout/notfound/failed) should
        # not stop escalation — that's the whole point of the escalation
        # loop.
        return None

    issue_id = _parse_issue_id(payload.get("tag"))
    if issue_id is None:
        logger.warning("tas calloutResult missing/invalid tag: %s", payload)
        return None

    try:
        return asyncio.run(_ack_issue_async(issue_id))
    except Exception:
        logger.exception("tas ack failed for issue=%s", issue_id)
        return None


def _on_connect(
    client: Any,
    userdata: dict[str, Any],
    flags: dict[str, Any],
    reason_code: Any,
    properties: Any = None,
) -> None:
    """Subscribe on every (re)connection so dropped sessions resume cleanly."""
    sn_key = userdata["sn_key"]
    result_topic = CALLOUT_RESULT_TOPIC.format(sn_key=sn_key)
    event_topic = CALL_EVENT_TOPIC.format(sn_key=sn_key)
    # callEvent is informational (DTMF, hangup) — subscribe so we can log
    # richer call-flow detail, but the answered ack only needs calloutResult.
    client.subscribe([(result_topic, 0), (event_topic, 0)])
    logger.info(
        "tas mqtt connected (reason=%s); subscribed result=%s event=%s",
        reason_code,
        result_topic,
        event_topic,
    )


def _on_disconnect(
    client: Any,
    userdata: dict[str, Any],
    disconnect_flags: Any,
    reason_code: Any,
    properties: Any = None,
) -> None:
    # paho's built-in reconnect loop handles the retry — just log the drop
    # so unexpected disconnects are visible in production.
    logger.warning("tas mqtt disconnected reason=%s; paho will reconnect", reason_code)


def _on_message(client: Any, userdata: dict[str, Any], message: Any) -> None:
    """paho callback — parse JSON and delegate to handle_message_payload."""
    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.exception("tas mqtt non-JSON message on topic=%s", message.topic)
        return

    if message.topic.startswith("phone-conn/callEvent/"):
        # Informational — log hangup / dtmf events but don't ack. Useful
        # for production debugging without flooding INFO logs.
        logger.debug("tas callEvent: %s", payload)
        return

    flipped = handle_message_payload(payload)
    if flipped is not None:
        logger.info("tas pickup processed: flipped=%d payload=%s", flipped, payload)


def _build_client(settings: Any) -> Any:
    """Construct + configure a paho client. Split out for testability."""
    if mqtt is None:
        raise RuntimeError("paho-mqtt is not installed. Add it to requirements.txt and reinstall.")

    parsed = urlparse(settings.tas_mqtt_broker_url)
    use_tls = parsed.scheme in ("tls", "mqtts", "ssl")
    host = parsed.hostname or "tasapi.cht.com.tw"
    port = parsed.port or (2883 if use_tls else 1883)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"lims-listener-{os.getpid()}",
        userdata={"sn_key": settings.tas_sn_key},
    )
    # Per TAS spec: username + password are both the API key.
    client.username_pw_set(settings.cht_api_key, settings.cht_api_key)
    if use_tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message

    return client, host, port


def main() -> int:
    """Listener entrypoint. Returns process exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()

    if not settings.tas_enabled:
        # Hard guard so a misconfigured container doesn't accidentally
        # subscribe to production topics. Same gate as the REST client.
        logger.info("TAS_ENABLED=False, exiting tas_mqtt_listener")
        return 0

    if not settings.tas_sn_key or not settings.cht_api_key:
        logger.error("TAS_SN_KEY / CHT_API_KEY missing — refusing to start listener")
        return 2

    client, host, port = _build_client(settings)

    # SIGTERM handler stops the network loop cleanly so docker stop doesn't
    # have to fall back to SIGKILL after 10s.
    def _shutdown(signum: int, frame: FrameType | None) -> None:
        logger.info("tas mqtt received signal=%d; stopping loop", signum)
        client.disconnect()
        client.loop_stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("tas mqtt connecting to %s:%d", host, port)
    client.connect(host, port, keepalive=60)
    client.loop_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
