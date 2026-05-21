"""Celery application + beat schedule.

Beat-scheduled tasks (e.g. issue escalation) live under ``app.workers``.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lims",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.escalation",
        "app.workers.email_sender",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "escalate-open-issues-every-minute": {
        "task": "app.workers.escalation.scan_and_escalate",
        "schedule": crontab(minute="*"),
    },
}
