# apps/worker

Celery worker entrypoint. Consumes background jobs (resume processing, embedding generation,
AI interview evaluation, roadmap generation, analytics rollups) from Redis and executes the
task modules defined in `apps/api/app/workers`. Built in Phase 4 (async resume processing is
the first consumer). See [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md#background-processing).
