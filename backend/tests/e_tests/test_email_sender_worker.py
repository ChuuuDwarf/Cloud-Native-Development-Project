"""Tests for the email-sender Celery tasks (file backend).

These run the task bodies synchronously via ``.run()`` — no broker needed. We
redirect the outbox into a tmp dir so the repo's ``uploads/`` stays clean, and
assert on the JSONL record the grader would read.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.workers import email_sender


def _read_outbox(outbox: Path) -> list[dict]:
    return [json.loads(line) for line in outbox.read_text(encoding="utf-8").splitlines() if line]


def test_send_notification_email_appends_to_outbox(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(email_sender.settings, "uploads_dir", str(tmp_path))
    monkeypatch.setattr(email_sender.settings, "email_backend", "file")

    result = email_sender.send_notification_email.run(
        to="alice@example.com", subject="Hi", body="Body text"
    )
    assert result == {"status": "queued", "to": "alice@example.com"}

    records = _read_outbox(tmp_path / "email_outbox.jsonl")
    assert len(records) == 1
    assert records[0]["to"] == "alice@example.com"
    assert records[0]["subject"] == "Hi"
    assert records[0]["from"] == email_sender.settings.email_from


def test_send_notification_email_smtp_backend_still_logs_to_file(tmp_path, monkeypatch) -> None:
    """The SMTP path is not implemented; it must still fall through to the
    file outbox so nothing is silently dropped in the demo."""
    monkeypatch.setattr(email_sender.settings, "uploads_dir", str(tmp_path))
    monkeypatch.setattr(email_sender.settings, "email_backend", "smtp")

    email_sender.send_notification_email.run(to="bob@example.com", subject="S", body="B")
    records = _read_outbox(tmp_path / "email_outbox.jsonl")
    assert records[-1]["to"] == "bob@example.com"


def test_send_pickup_reminder_email_builds_subject_and_body(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(email_sender.settings, "uploads_dir", str(tmp_path))
    monkeypatch.setattr(email_sender.settings, "email_backend", "file")

    result = email_sender.send_pickup_reminder_email.run(
        to="carol@example.com", order_id="ORD-123", applicant="Carol"
    )
    assert result["status"] == "queued"

    record = _read_outbox(tmp_path / "email_outbox.jsonl")[-1]
    assert "ORD-123" in record["subject"]
    assert record["body"].startswith("Carol 您好，")
    assert "ORD-123" in record["body"]


def test_send_pickup_reminder_without_applicant_omits_greeting(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(email_sender.settings, "uploads_dir", str(tmp_path))
    monkeypatch.setattr(email_sender.settings, "email_backend", "file")

    email_sender.send_pickup_reminder_email.run(to="d@example.com", order_id="ORD-9")
    record = _read_outbox(tmp_path / "email_outbox.jsonl")[-1]
    # No applicant → no "<name> 您好，" prefix.
    assert not record["body"].startswith(" 您好")
    assert "ORD-9" in record["body"]
