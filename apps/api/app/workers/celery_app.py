from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "careerai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Task modules are registered here as they're introduced — resume processing (Phase 4) is
# the first consumer (docs/ARCHITECTURE.md §5, apps/worker/README.md).
celery_app.autodiscover_tasks(["app.workers"])
