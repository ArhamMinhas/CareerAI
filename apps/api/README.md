# apps/api

FastAPI backend. Clean layered architecture — see [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md).

```
app/
  api/            versioned route handlers only (thin — no business logic)
  core/           config, security, dependency injection, logging setup
  models/         SQLAlchemy/SQLModel ORM models (one module per domain area)
  schemas/        Pydantic request/response schemas
  services/       business logic (resume scoring, matching, roadmap generation, ...)
  repositories/   data access layer (query construction, no business rules)
  ai/             LLM provider abstraction, prompt loading, RAG orchestration
  ml/             ML model loading + inference (calls into top-level ml/ package)
  workers/        Celery task definitions shared with apps/worker
  utils/          cross-cutting helpers
tests/            pytest suite (unit + integration + API tests)
```

Built starting in Phase 1.
