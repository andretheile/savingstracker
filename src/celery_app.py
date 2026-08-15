"""Celery application factory with Redis broker and beat schedule."""

from celery import Celery
from celery.schedules import crontab

from src.config import settings

celery_app = Celery(
    "savingstracker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.scheduler.tasks"],
)

# ── Celery configuration ──────────────────────────────────
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="Europe/Berlin",
    enable_utc=True,
    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Result expiry
    result_expires=86400,  # 24 hours
)

# ── Beat schedule (periodic tasks) ────────────────────────
# Celery 5.6 ScheduleEntry does not accept a description= key.
celery_app.conf.beat_schedule = {
    "monthly-report-all-users": {
        "task": "src.scheduler.tasks.generate_all_monthly_reports",
        "schedule": crontab(day_of_month="1", hour="8", minute="0"),
    },
    "daily-sync-reminder": {
        "task": "src.scheduler.tasks.check_stale_connections",
        "schedule": crontab(hour="6", minute="0"),
    },
}
