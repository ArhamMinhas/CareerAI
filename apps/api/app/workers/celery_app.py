from celery import Celery

from app.core.config import settings

# `include` explicitly imports each task module so its `@celery_app.task`-decorated functions
# register — `autodiscover_tasks` was tried first, but it only ever looks for a module
# literally named `tasks.py` inside each package, never arbitrarily-named ones like
# `resume_tasks.py`, so it silently registered nothing (confirmed via `celery -A ... worker`
# printing an empty `[tasks]` list at startup). Explicit imports here work regardless of
# filename and stay legible as more task modules are added — embedding generation, AI
# interview evaluation, roadmap generation, analytics rollups (apps/worker/README.md).
celery_app = Celery(
    "careerai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.resume_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
