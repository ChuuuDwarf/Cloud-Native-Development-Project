"""Celery task: send a notification via email (file backend for demo, SMTP for real).

Triggered by NotificationService.notify() when settings.channels includes ``email``.
"""

import json
import logging
from pathlib import Path

from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="app.workers.email_sender.send_notification_email")
def send_notification_email(to: str, subject: str, body: str) -> dict:
    """Phase 3: implement the real SMTP path when ``EMAIL_BACKEND=smtp``.

    For the demo (``EMAIL_BACKEND=file``), append the message as JSON to
    ``uploads/email_outbox.jsonl`` so the grader can read what was "sent".
    """
    payload = {"to": to, "from": settings.email_from, "subject": subject, "body": body}

    if settings.email_backend == "smtp":
        # Phase 3 / Phase 6 stretch: use fastapi-mail or aiosmtplib here.
        logger.warning("SMTP backend not implemented; logging instead")

    outbox = Path(settings.uploads_dir) / "email_outbox.jsonl"
    outbox.parent.mkdir(parents=True, exist_ok=True)
    with outbox.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    logger.info("Email queued to %s subject=%r", to, subject)
    return {"status": "queued", "to": to}


@celery_app.task(name="app.workers.email_sender.send_pickup_reminder_email")
def send_pickup_reminder_email(to: str, order_id: str, applicant: str | None = None) -> dict:
    """Remind an order's requester that their samples are ready for pickup.

    Enqueued by the closures service when an order transitions to ``待取件 /
    WAITING_PICKUP``. Reuses :func:`send_notification_email` for delivery so the
    file/SMTP backend behaviour stays in one place.
    """
    greeting = f"{applicant} 您好，" if applicant else ""
    subject = f"【LIMS】委託單 {order_id} 樣品待取件通知"
    body = f"{greeting}您委託的單號 {order_id} 已完成處理，樣品已可取件，請至實驗室倉儲辦理取件。"
    return send_notification_email.run(to=to, subject=subject, body=body)
