"""Celery application + beat schedule.

Beat-scheduled tasks (e.g. issue escalation) live under ``app.workers``.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lims",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.escalation",
        "app.workers.email_sender",
        "app.workers.experiment_tasks",
        "app.workers.phone_sender",
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
    "escalate-open-issues": {
        "task": "app.workers.escalation.scan_and_escalate",
        # Safety net only — ETA tasks (escalate_specific_issue) are the
        # primary driver (Option C). This sweep catches issues whose ETA
        # task was dropped (worker restart, lost broker message, etc.).
        "schedule": 60.0,
    },
    # 進度自動推進：每 2 秒檢查一次，依各 WIP 的 next_progress_at（隨機 3/5/8 秒）+1%。
    "tick-experiment-progress": {
        "task": "app.workers.experiment_tasks.tick_progress",
        "schedule": 2.0,
    },
}
