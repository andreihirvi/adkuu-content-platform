"""
Celery application configuration.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


# Create Celery application
celery_app = Celery(
    "reddit_content_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.mine_opportunities",
        "app.tasks.generate_content",
        "app.tasks.collect_analytics",
        "app.tasks.check_account_health",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Task routing
    task_routes={
        "app.tasks.mine_opportunities.*": {"queue": "opportunity-mining"},
        "app.tasks.generate_content.*": {"queue": "content-generation"},
        "app.tasks.collect_analytics.*": {"queue": "analytics"},
        "app.tasks.check_account_health.*": {"queue": "account-health"},
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule for periodic tasks
    beat_schedule={
        # Mine opportunities every 15 minutes
        "mine-opportunities-periodic": {
            "task": "app.tasks.mine_opportunities.scheduled_mining",
            "schedule": crontab(minute=f"*/{settings.MINING_INTERVAL_MINUTES}"),
            "options": {"queue": "opportunity-mining"},
        },

        # Collect analytics every 30 minutes
        "collect-analytics-periodic": {
            "task": "app.tasks.collect_analytics.collect_all_analytics",
            "schedule": crontab(minute="*/30"),
            "options": {"queue": "analytics"},
        },

        # Check account health every hour
        "check-account-health-periodic": {
            "task": "app.tasks.check_account_health.check_all_accounts_health",
            "schedule": crontab(minute=0),  # Every hour at :00
            "options": {"queue": "account-health"},
        },

        # Update learning features daily at 3 AM UTC
        "update-learning-features-daily": {
            "task": "app.tasks.collect_analytics.update_learning_features",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "analytics"},
        },

        # Expire old opportunities daily at 4 AM UTC
        "expire-old-opportunities-daily": {
            "task": "app.tasks.mine_opportunities.expire_old_opportunities",
            "schedule": crontab(hour=4, minute=0),
            "options": {"queue": "opportunity-mining"},
        },
    },

    # Worker settings
    worker_send_task_events=True,
    task_send_sent_event=True,
)


# Optional: Configure for development/testing
if settings.DEBUG:
    celery_app.conf.update(
        task_always_eager=False,  # Set to True to run tasks synchronously in dev
        task_eager_propagates=True,
    )
