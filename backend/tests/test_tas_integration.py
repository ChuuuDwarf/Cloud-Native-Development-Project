"""Unit tests for the TAS (中華電信 phone alert) integration.

Covers four corners of the pipeline, all without real network I/O:

1. REST callout no-ops when ``TAS_ENABLED`` is False.
2. REST callout posts the spec-shaped JSON with the right headers.
3. MQTT message handler acks the issue when ``status == "answered"``.
4. Celery callout task skips cleanly when the recipient has no phone.

Tests live at the top of ``backend/tests/`` (alongside other module-level
tests like ``test_route_integration.py``) instead of under the ``e_tests/``
sub-package because TAS is a cross-cutting infra concern, not E's module.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services import cht_tas as tas_module
from app.services.cht_tas import CHTTASClient, CHTTASError
from app.workers import phone_sender, tas_mqtt_listener

# ---------------------------------------------------------------------------
# Helpers — pytest fixtures fashioned to swap in/out the lru-cached settings.
# ---------------------------------------------------------------------------


def _fake_settings(**overrides):
    """Build a stand-in Settings-shaped object for monkeypatching.

    Default values mirror the ones a non-configured local dev box would
    produce; tests override the bits they care about.
    """
    defaults = {
        "tas_enabled": True,
        "cht_api_key": "test-key",
        "cht_service_number": "0233000000",
        "cht_base_url": "https://example.invalid/apis/CHTIoT",
        "tas_sn_key": "test-sn",
        "tas_mqtt_broker_url": "tls://example.invalid:2883",
        "database_url": "postgresql+asyncpg://x:y@localhost/none",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# 1. test_callout_no_op_when_disabled
# ---------------------------------------------------------------------------


def test_callout_no_op_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """TAS_ENABLED=False short-circuits the REST callout cleanly.

    The client must refuse to fire (raises CHTTASError per its public
    contract) and ``httpx.post`` must never be invoked. Belt-and-braces:
    we patch httpx so even if the guard were missing the test would catch
    the leak instead of hitting the network.
    """
    monkeypatch.setattr(tas_module, "get_settings", lambda: _fake_settings(tas_enabled=False))

    called: list[str] = []

    def _boom(*args, **kwargs):
        called.append(args[0])
        raise AssertionError("httpx.post must not be called when TAS_ENABLED=False")

    monkeypatch.setattr(httpx, "post", _boom)

    client = CHTTASClient()
    assert client.configured is False

    with pytest.raises(CHTTASError, match="not configured"):
        client.callout(phones=["0912000000"], text="hi")

    assert called == []


# ---------------------------------------------------------------------------
# 2. test_callout_posts_correct_payload
# ---------------------------------------------------------------------------


def test_callout_posts_correct_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """The REST callout hits the right URL with the expected payload shape.

    The TAS spec demands ``serviceNumber``, ``phones``, and (for our
    correlation) ``tags`` to round-trip through the ``calloutResult``
    MQTT event. We also assert the ``x-api-key`` header is set — TAS
    rejects requests without it.
    """
    monkeypatch.setattr(tas_module, "get_settings", lambda: _fake_settings())

    captured: dict[str, object] = {}

    def _fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        # Mimic the success envelope TAS returns.
        return httpx.Response(200, json={"status": "ok", "groupId": "g-123"})

    monkeypatch.setattr(httpx, "post", _fake_post)

    client = CHTTASClient()
    body = client.callout(phones=["0912000000"], text="alert", tags=["issue:abc"])

    assert body["groupId"] == "g-123"
    assert captured["url"].endswith("/phone-conn/v1/callout")
    # CHT TAS auth header — lower-cased per the spec sample.
    assert captured["headers"]["x-api-key"] == "test-key"
    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["serviceNumber"] == "0233000000"
    assert payload["phones"] == ["0912000000"]
    assert payload["tags"] == ["issue:abc"]
    # IVR data is required by TAS even for a single-shot alert call —
    # missing keys here would surface as MQTT callActionDebug errors.
    assert set(payload["ivrData"].keys()) >= {"welcomeText", "text", "byeText", "node"}


# ---------------------------------------------------------------------------
# 3. test_listener_marks_notification_read_on_answered
# ---------------------------------------------------------------------------


def test_listener_marks_notification_read_on_answered(monkeypatch: pytest.MonkeyPatch) -> None:
    """A TAS ``answered`` message triggers the ack path for the tagged issue.

    We feed the message dict straight into ``handle_message_payload`` so
    the test doesn't need a paho client. The async ack helper is replaced
    by a recorder — that's the seam between the listener and the DB layer
    and is exactly what we want to assert on without spinning a real
    NotificationService.
    """
    issue_id = uuid.uuid4()

    recorded: list[uuid.UUID] = []

    async def _fake_ack(target_id):
        recorded.append(target_id)
        return 1

    monkeypatch.setattr(tas_mqtt_listener, "_ack_issue_async", _fake_ack)

    payload = {
        "groupId": "g-1",
        "phone": "****0000",
        "status": "answered",
        "statusCode": 200,
        # TAS returns ``tag`` as a string per spec; the originating callout
        # encoded our issue id with the ``issue:`` prefix.
        "tag": f"issue:{issue_id}",
        "time": "2026-03-24T05:26:37.623859240Z",
    }

    flipped = tas_mqtt_listener.handle_message_payload(payload)

    assert recorded == [issue_id]
    assert flipped == 1

    # Other statuses (reject/busy/timeout) must NOT ack — escalation should
    # keep firing until someone actually picks up.
    recorded.clear()
    for bad_status in ("reject", "busy", "timeout", "notfound", "failed"):
        result = tas_mqtt_listener.handle_message_payload({**payload, "status": bad_status})
        assert result is None
    assert recorded == []


# ---------------------------------------------------------------------------
# 4. test_send_tas_callout_task_skips_when_user_has_no_phone
# ---------------------------------------------------------------------------


def test_send_tas_callout_task_skips_when_user_has_no_phone() -> None:
    """The callout task is a no-op when the recipient list is empty.

    The phone lookup happens upstream in ``NotificationService`` — by the
    time ``send_callout`` runs, an empty ``phones`` list is the canonical
    "user had no phone" signal. The task must short-circuit without
    constructing a TAS client (and therefore without dialling anything).
    """
    # If the task ever instantiated CHTTASClient with an empty phones list,
    # the patched constructor would let us catch it. We *don't* want it called.
    with patch.object(phone_sender, "CHTTASClient") as fake_ctor:
        result = phone_sender.send_callout.run(phones=[], title="t", body="b")

    assert result == {"status": "skipped", "reason": "no recipients"}
    fake_ctor.assert_not_called()


# ---------------------------------------------------------------------------
# Bonus: covers the _parse_issue_id helper edge cases. Keeps the listener's
# tag-decode logic regression-proof without a full pipeline test.
# ---------------------------------------------------------------------------


def test_parse_issue_id_variants() -> None:
    """Tag parser accepts string and list forms; rejects garbage."""
    valid_uuid = uuid.uuid4()
    assert tas_mqtt_listener._parse_issue_id(f"issue:{valid_uuid}") == valid_uuid
    assert tas_mqtt_listener._parse_issue_id([f"issue:{valid_uuid}"]) == valid_uuid
    assert tas_mqtt_listener._parse_issue_id("notes:not-a-uuid") is None
    assert tas_mqtt_listener._parse_issue_id("issue:not-a-uuid") is None
    assert tas_mqtt_listener._parse_issue_id(None) is None
    assert tas_mqtt_listener._parse_issue_id([]) is None


# ---------------------------------------------------------------------------
# 5. Listener main() exits cleanly when TAS_ENABLED=False — same gate as the
# REST client; keeps CI / local dev from crash-looping the listener container.
# ---------------------------------------------------------------------------


def test_listener_main_exits_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tas_mqtt_listener, "get_settings", lambda: _fake_settings(tas_enabled=False)
    )
    # Belt-and-braces: ensure the MQTT client builder is never called.
    monkeypatch.setattr(
        tas_mqtt_listener,
        "_build_client",
        MagicMock(side_effect=AssertionError("_build_client must not be called when disabled")),
    )

    assert tas_mqtt_listener.main() == 0
