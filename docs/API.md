# CareerAI — API Design

Status: Phase 0 design. Implemented incrementally starting Phase 1; each phase adds the
endpoints it needs (see [ROADMAP.md](./ROADMAP.md)).

## 1. Conventions

- **Base path:** `/api/v1`. Breaking changes ship as `/api/v2` alongside `v1` (not an
  in-place break) — the frontend pins a version via `packages/types`.
- **Auth:** `Authorization: Bearer <supabase JWT>` on every route except `/auth/*` and public
  landing-page content endpoints. Verified via FastAPI dependency (`get_current_user`), which
  loads the local `users` row (for role/permissions) after validating the JWT signature.
- **Content type:** `application/json` except file upload (`multipart/form-data`) and SSE
  streaming responses (AI chat/interview feedback), which use `text/event-stream`.
- **Pagination:** cursor-based for feeds that grow unbounded (jobs, notifications, audit logs):
  `?limit=20&cursor=<opaque>` → response includes `next_cursor`. Offset-based
  (`?page=1&page_size=20`) only for small, stable admin lists.
- **Filtering/sorting:** `?filter[field]=value` for filters, `?sort=-created_at,title` for
  sorting (leading `-` = descending). Documented per-endpoint, not a generic passthrough to SQL.
- **Idempotency:** mutating AI-triggering endpoints (`/resumes/{id}/analyze`,
  `/interviews/{id}/answer`) accept an `Idempotency-Key` header to avoid double-billing on
  client retries.

## 2. Standard response envelope

```json
{
  "data": { "...": "..." },
  "meta": { "request_id": "req_...", "next_cursor": null }
}
```

## 3. Standard error format

```json
{
  "error": {
    "code": "RESUME_NOT_FOUND",
    "message": "Resume 3f2c... was not found.",
    "details": null,
    "request_id": "req_..."
  }
}
```

- HTTP status communicates the class of error (400/401/403/404/409/422/429/500).
- `code` is a stable machine-readable string the frontend can switch on for localized copy.
- Stack traces are never serialized to the client (spec §44) — only logged server-side with
  `request_id` as the correlation key.
- Validation errors (422) include `details` as a field→message map from Pydantic.

## 4. Rate limiting

Token-bucket per user (Redis-backed): general API 120 req/min, AI-triggering endpoints
(resume analyze, career analyze, interview answer, RAG chat) 20 req/min, stricter still on
unauthenticated endpoints. `429` responses include `Retry-After`.

## 5. Endpoint catalog

### Auth (delegates to Supabase; thin wrapper for profile bootstrap)
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
POST   /api/v1/auth/password-reset
GET    /api/v1/auth/me
```

### Profile
```
GET    /api/v1/profile
PATCH  /api/v1/profile
POST   /api/v1/profile/education
PATCH  /api/v1/profile/education/{id}
DELETE /api/v1/profile/education/{id}
POST   /api/v1/profile/experience
PATCH  /api/v1/profile/experience/{id}
DELETE /api/v1/profile/experience/{id}
POST   /api/v1/profile/projects
PATCH  /api/v1/profile/projects/{id}
DELETE /api/v1/profile/projects/{id}
POST   /api/v1/career-goals
GET    /api/v1/career-goals
```

### Resumes
```
POST   /api/v1/resumes/upload              -> 202 Accepted, enqueues processing job
GET    /api/v1/resumes                     -> list (paginated)
GET    /api/v1/resumes/{id}
GET    /api/v1/resumes/{id}/status         -> lightweight polling endpoint
POST   /api/v1/resumes/{id}/analyze        -> recompute score (idempotency-key required)
GET    /api/v1/resumes/{id}/versions
DELETE /api/v1/resumes/{id}
```

### Skills
```
GET    /api/v1/skills                      -> taxonomy browse/search
GET    /api/v1/skills/{id}
GET    /api/v1/skills/gaps?target_role=ai_engineer
POST   /api/v1/skills/gaps/refresh
```

### Career
```
POST   /api/v1/career/analyze              -> recommendation engine (rule + ML + embeddings)
GET    /api/v1/career/recommendations
GET    /api/v1/career/roadmap
POST   /api/v1/career/roadmap/generate
PATCH  /api/v1/career/roadmap/items/{id}   -> mark complete, etc.
```

### Jobs
```
GET    /api/v1/jobs                        -> filter/sort/paginate, keyword or semantic (?q=)
GET    /api/v1/jobs/{id}
POST   /api/v1/jobs/match                  -> trigger/refresh personalized matches
GET    /api/v1/matches                     -> ranked list for current user
POST   /api/v1/applications
GET    /api/v1/applications
PATCH  /api/v1/applications/{id}
```

### Interviews
```
POST   /api/v1/interviews                  -> create session (mode, target_role)
GET    /api/v1/interviews/{id}
POST   /api/v1/interviews/{id}/answer      -> submit answer, streams evaluation (SSE)
GET    /api/v1/interviews/{id}/evaluation
GET    /api/v1/interviews                  -> history
```

### RAG / AI chat
```
POST   /api/v1/ai/chat                     -> grounded Q&A, streams response + sources (SSE)
```

### Analytics
```
GET    /api/v1/analytics/market            -> trends, filters: region, role, date range
GET    /api/v1/analytics/skills            -> demand, growth, salary correlation
GET    /api/v1/analytics/dashboard         -> personalized executive-overview payload
```

### Notifications
```
GET    /api/v1/notifications
PATCH  /api/v1/notifications/{id}/read
```

### Admin (role=ADMIN only)
```
GET    /api/v1/admin/users
PATCH  /api/v1/admin/users/{id}
GET    /api/v1/admin/jobs
POST   /api/v1/admin/jobs
GET    /api/v1/admin/skills
POST   /api/v1/admin/skills
GET    /api/v1/admin/ai-usage
GET    /api/v1/admin/model-metrics
GET    /api/v1/admin/system-health
```

## 6. OpenAPI → shared types

FastAPI auto-generates `openapi.json`; a CI/dev script (`packages/types`) runs
`openapi-typescript` against it so `apps/web` consumes generated request/response types instead
of hand-maintained duplicates. Domain types that predate the backend (used for design work) live
in `packages/types/domain/` and are reconciled with generated types once endpoints exist.

## 7. Streaming responses

AI chat and interview evaluation stream via Server-Sent Events so the UI can render tokens as
they arrive rather than waiting on a full completion — critical for perceived performance on
LLM-backed endpoints. Each SSE event is a typed JSON payload (`{"type": "token" | "source" |
"done" | "error", ...}`), not raw provider output, so the frontend never depends on a specific
LLM provider's stream shape.
