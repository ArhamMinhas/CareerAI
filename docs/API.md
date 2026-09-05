# CareerAI — API Design

Status: Phase 0 design. Implemented incrementally starting Phase 1; each phase adds the
endpoints it needs (see [ROADMAP.md](./ROADMAP.md)).

## 1. Conventions

- **Base path:** `/api/v1`. Breaking changes ship as `/api/v2` alongside `v1` (not an
  in-place break) — the frontend pins a version via `packages/types`.
- **Auth:** `Authorization: Bearer <supabase JWT>` on every route except `/auth/*` and public
  landing-page content endpoints. Verified via FastAPI dependency (`get_current_user`), which
  loads the local `users` row (for role/permissions) after validating the JWT signature.
- **Content type:** `application/json` except file upload (`multipart/form-data`). No endpoint
  currently streams via SSE — see §7 for why RAG/interview evaluation ship as plain JSON instead.
- **Pagination:** cursor-based for feeds that grow unbounded (jobs, notifications, audit logs):
  `?limit=20&cursor=<opaque>` → response includes `next_cursor`. Offset-based
  (`?page=1&page_size=20`) only for small, stable admin lists.
- **Filtering/sorting:** `?filter[field]=value` for filters, `?sort=-created_at,title` for
  sorting (leading `-` = descending). Documented per-endpoint, not a generic passthrough to SQL.
- **Idempotency:** mutating AI-triggering endpoints (`/resumes/{id}/analyze`,
  `/interviews/{id}/answer`, `/rag/query`, `/learning-roadmap/generate`) accept an
  `Idempotency-Key` header to avoid double-billing on client retries. `/rag/query` (Phase 9) was
  the first to back it with a real `SET NX` reservation + cached-response replay, not just a
  required-header check — see `app/core/idempotency.py`; `/learning-roadmap/generate` (Phase 10)
  and `/interviews/{id}/answer` (Phase 11) each reuse the same module with their own `scope`.
  `POST /interviews` itself needs no Idempotency-Key — it makes no LLM call.

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
(resume analyze, career analyze, interview answer, RAG chat, learning-roadmap generation)
20 req/min, stricter still on unauthenticated endpoints. `429` responses include `Retry-After`.
Real (not just documented) for `/rag/query` (Phase 9) and `/learning-roadmap/generate`
(Phase 10) via `app/core/rate_limit.py`, both real per-user token buckets. Everything else in
this section — the general 120 req/min limit, and resume-analyze/career-analyze/interview-answer
specifically — remains aspirational: `rate_limit_default_per_minute`/`rate_limit_ai_per_minute`
are defined in config but only the two routes above actually enforce anything. Phase 15
("Production Hardening") owns the general, all-routes rollout.

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

### Profile (Phase 3)

`Profile` is 1:1 with `User`, created lazily on first `GET`/`PATCH /profile` rather than at
signup. Education/experience/projects/skills are NOT nested in the profile response — each is
its own resource, fetched separately (the frontend does this as one `Promise.all`). Every
sub-resource route is scoped to the caller's own profile; an id that exists but belongs to a
different user 404s rather than 403s, so ownership isn't leaked.

```
GET    /api/v1/profile
PATCH  /api/v1/profile

GET    /api/v1/profile/education
POST   /api/v1/profile/education
PATCH  /api/v1/profile/education/{id}
DELETE /api/v1/profile/education/{id}        -> soft delete (deleted_at)

GET    /api/v1/profile/experience
POST   /api/v1/profile/experience
PATCH  /api/v1/profile/experience/{id}
DELETE /api/v1/profile/experience/{id}       -> soft delete

GET    /api/v1/profile/projects
POST   /api/v1/profile/projects
PATCH  /api/v1/profile/projects/{id}
DELETE /api/v1/profile/projects/{id}         -> soft delete

GET    /api/v1/profile/skills                -> the caller's own UserSkill rows
POST   /api/v1/profile/skills                -> {skill_name, proficiency}; get-or-creates the
                                                 Skill taxonomy row by name, 409 if already added
PATCH  /api/v1/profile/skills/{id}           -> proficiency only
DELETE /api/v1/profile/skills/{id}           -> hard delete (not soft — see docs/DATABASE.md §1)

GET    /api/v1/career-goals
POST   /api/v1/career-goals
PATCH  /api/v1/career-goals/{id}
DELETE /api/v1/career-goals/{id}             -> hard delete
```

### Resumes (Phase 4)

Not paginated — a user has few resumes, not an unbounded feed (docs/API.md §1's cursor-
pagination rule is for genuinely unbounded lists like jobs/notifications). `GET /resumes/{id}`
includes a short-lived signed download URL (`file_download_url`) rather than a permanent public
one — the storage bucket is private, resumes are personal documents.

```
POST   /api/v1/resumes/upload              -> multipart/form-data, 202 Accepted, enqueues processing
GET    /api/v1/resumes                     -> full list, newest first
GET    /api/v1/resumes/{id}                -> includes structured_data, score_breakdown, file_download_url
GET    /api/v1/resumes/{id}/status         -> lightweight polling endpoint
POST   /api/v1/resumes/{id}/analyze        -> re-score; Idempotency-Key required (400 if missing),
                                               409 if this resume is already processing — see
                                               docs/ROADMAP.md Phase 4 for what's and isn't covered
GET    /api/v1/resumes/{id}/versions       -> one snapshot per completed analysis, newest first
DELETE /api/v1/resumes/{id}                -> soft delete
```

### Skills
```
GET    /api/v1/skills                      -> ?q= search (Phase 3: manual-entry autocomplete, auth required)
GET    /api/v1/skills/gaps?target_role=    -> the caller's cached gap analysis; auto-computes on first read
POST   /api/v1/skills/gaps/refresh?target_role=  -> forces a fresh recomputation
GET    /api/v1/skills/curated              -> every skill with curated /skills/[slug] content — public, sitemap generator only
GET    /api/v1/skills/{id_or_slug}         -> skill detail (public — /skills/[slug])
```
`target_role` is free text (e.g. from `career_goals.target_role`), resolved server-side to a
`career_paths` row by slug or title match (app/services/career_paths.py) — not a slug or id
itself. `gaps`/`gaps/refresh` are the only skills routes requiring auth; `{id_or_slug}` and
`curated` are public like the career-path routes below, since they back indexable pages too.

### Careers (SEO surface — no auth required)
```
GET    /api/v1/careers                     -> list published career paths
GET    /api/v1/careers/{slug}              -> career path detail + required skills + related paths
```

### Public content (SEO surface — no auth required)

Backs the indexable `/careers/[slug]`, `/skills/[slug]`, `/companies/[slug]`, `/resources/[slug]`
pages in [SEO.md](./SEO.md); reads `career_paths`/`resources`/`companies` from
[DATABASE.md §2.6](./DATABASE.md#26-public-content--seo). Public, cacheable (long-TTL,
`Cache-Control` set for CDN caching at the edge), and unauthenticated — these are the routes
Next.js SSR/ISR calls at build/revalidate time, not something a logged-in user's browser hits
directly per request. `/careers*` shipped in Phase 6 (see its own section above); companies/jobs
shipped in Phase 7 (see below) — routed by `slug`, not `{id}` as this section originally said,
matching every other public content type here (see `Company`'s model docstring); resources
shipped in Phase 9.
```
GET    /api/v1/companies/{slug}
GET    /api/v1/companies/{slug}/jobs       -> jobs at this company (for the company page)
GET    /api/v1/resources                   -> list published articles
GET    /api/v1/resources/{slug}            -> article detail + related_resources (embedding similarity)
```
No `category`/`tag` filtering on the list endpoint, unlike this section's original draft —
matches `GET /careers`'s established "curated catalog is small by design, not an unbounded feed"
precedent; add filtering if/when the catalog's real size ever justifies it.

### Career
```
POST   /api/v1/career/analyze              -> still unbuilt; a distinct future concept from
                                               career-recommendations below, not a duplicate
```
The four routes this section originally sketched under `/career/*` (`recommendations`,
`roadmap`, `roadmap/generate`, `roadmap/items/{id}`) were never implemented at that path — real
routers in this codebase are consistently flat-hyphenated (`career-goals`, `career-recommendations`,
`careers`), never nested under `/career/`. `GET /api/v1/career-recommendations` shipped in Phase
8 (see its own section below); the roadmap routes shipped in Phase 10 as `/api/v1/learning-roadmap*`
(see "Learning Roadmap" below) — same convention mismatch Phase 9 already found and fixed for
its own `/career/roadmap` sibling, `GET /api/v1/career-recommendations`.

### Learning Roadmap (Phase 10)
```
GET    /api/v1/learning-roadmap             -> stored roadmap for ?target_role=; 404 if none
                                               generated yet (no auto-generate-on-read, unlike
                                               GET /skills/gaps — this route has a real LLM cost
                                               component, see POST /generate below)
POST   /api/v1/learning-roadmap/generate    -> sequences the user's skill gaps deterministically
                                               (docs/AI_ARCHITECTURE.md §8's Learning Planner),
                                               then a bounded LLM overview call that can fail
                                               without failing the request; Idempotency-Key
                                               required, real per-user rate limit (429 +
                                               Retry-After) — reuses the same infra Phase 9 built
                                               for /rag/query
PATCH  /api/v1/learning-roadmap/items/{id}  -> toggle one step's completion; ownership-checked,
                                               no LLM/rate-limit involved
DELETE /api/v1/learning-roadmap             -> soft-deletes the active roadmap for ?target_role=,
                                               so a fresh POST /generate can start over
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

### Interviews (Phase 11)
```
POST   /api/v1/interviews                  -> create session (mode, optional target_role) + first
                                               question. No LLM call (pure retrieval from a
                                               curated question bank) — no Idempotency-Key
                                               required, unlike every other AI-triggering POST
                                               below
GET    /api/v1/interviews                  -> history, cursor-paginated (§1) — a user can start
                                               unboundedly many practice sessions
GET    /api/v1/interviews/analytics        -> real aggregates over the user's own completed
                                               sessions: total completed, average overall/per-
                                               dimension scores, last-5 trend. Registered before
                                               /{id} for the same route-ordering reason as
                                               /skill-gaps' /gaps
GET    /api/v1/interviews/{id}             -> full session detail: every question asked so far
                                               with its answer/evaluation if already submitted.
                                               Folds the separate GET .../evaluation this section
                                               originally sketched into this one response — the
                                               split only made sense paired with the SSE-streaming
                                               answer route it sat next to, which was never built
                                               (see §7)
POST   /api/v1/interviews/{id}/answer      -> the one AI-triggering route. Idempotency-Key
                                               required, real per-user rate limit (429 +
                                               Retry-After) — reuses the same infra Phase 9 built
                                               for /rag/query. Evaluates the answer, persists it,
                                               and either creates the next question or completes
                                               the session with a real overall_score
DELETE /api/v1/interviews/{id}             -> soft-delete
```

### RAG / AI chat (Phase 9)
```
POST   /api/v1/rag/query                   -> grounded Q&A + citations; Idempotency-Key required,
                                               real per-user token-bucket rate limit (429 +
                                               Retry-After), backs /dashboard/ask
```
Shipped as `POST /api/v1/rag/query`, a single non-streaming JSON response — not the `/api/v1/
ai/chat` SSE-streaming shape this section originally sketched. Answers are capped at 600 output
tokens (short by design), and both the real rate limiter and the real Idempotency-Key
reserve/replay/cache logic are far simpler to build correctly against one atomic response than
against a stream that would need to be cached and replayed chunk-by-chunk — a deliberate
trade-off given this phase's mandate to build both controls for real rather than defer them
again. Revisit streaming if/when a longer-form answer format makes non-streaming latency a real
problem.

### Analytics (Phase 12)
```
GET    /api/v1/analytics/market            -> catalog-wide skill/job/salary/career-path trends,
                                               not personalized. ?date_from=/?date_to= filter the
                                               two genuine time series (job posting volume,
                                               median salary) only — top-growing-skills/trending-
                                               career-paths always reflect the current snapshot,
                                               which doesn't have a sensible historical-range
                                               reading the way a time series does. No `region`
                                               filter (the original sketch here) — SkillDemand/
                                               SalaryData dropped that column in Phase 8, real
                                               US-only data (see docs/DATABASE.md §2.5)
GET    /api/v1/analytics/skills            -> the whole curated skill catalog (broader than
                                               GET /skills/{slug}'s single-skill page): demand,
                                               growth, and avg_associated_salary — a real average
                                               of SalaryData rows for job categories/seniorities
                                               that require each skill, not a fabricated
                                               correlation coefficient. ?sort=/?limit= only, no
                                               cursor pagination (the catalog is curated/seeded,
                                               ~66 rows, matching §1's "small, stable" exemption)
GET    /api/v1/analytics/dashboard         -> personalized executive-overview payload — a real
                                               rollup of the current user's own already-computed
                                               state (resume, skill gaps, interviews, roadmap,
                                               job-search funnel). Strictly read-only: unlike
                                               GET /skills/gaps, it never triggers a fresh
                                               computation for a section that has no data yet
```
All three are pure deterministic SQL aggregation — zero LLM calls (docs/AI_ARCHITECTURE.md §8 has
no Analytics agent) — so none needs an Idempotency-Key or rate limit. Kept behind auth like every
other `/dashboard/*`-backing route for consistency, not because the underlying market/skill data
is confidential: `GET /skills/{slug}` already publicly exposes one skill's full demand history
unauthenticated, so the catalog-wide views here are already reconstructable without login.

### Notifications
```
GET    /api/v1/notifications
PATCH  /api/v1/notifications/{id}/read
```
Not built in Phase 12 — the roadmap's own one-liner for that phase ("skill trends, job trends,
salary analytics, career analytics, candidate analytics dashboards") never named notifications,
and no feature yet generates a notification-worthy event to back this with real data.

### Admin (role=ADMIN only, Phase 13)
```
GET    /api/v1/admin/users          -> cursor-paginated, optional ?q= substring filter on email
PATCH  /api/v1/admin/users/{id}     -> body: {role}. The only real admin-mutable field on User —
                                        blocks an admin from changing their OWN role away from
                                        ADMIN (403), since there is no other path to ADMIN besides
                                        direct DB access
GET    /api/v1/admin/jobs           -> cursor-paginated, includes inactive jobs (unlike the
                                        public /jobs list)
POST   /api/v1/admin/jobs           -> creates a real Job + a real embedding (same pattern as
                                        the Adzuna ingestion pipeline), requires an existing
                                        company_id, optionally accepts required_skill_names
GET    /api/v1/admin/skills         -> cursor-paginated, includes a has_curated_content flag
                                        (whether seo_summary/embedding is set) — an admin-specific
                                        view, not a duplicate of the public /skills autocomplete
POST   /api/v1/admin/skills         -> a real create — 409 on a slug collision, unlike the
                                        internal get_or_create_skill helper other features use,
                                        which silently returns the existing row instead
GET    /api/v1/admin/ai-usage       -> real aggregates over ai_conversations (Phase 5): call
                                        counts/tokens/avg latency grouped by feature and by
                                        model, optional ?date_from=/?date_to=. No dollar-cost
                                        figure — no real pricing constants exist in this codebase
GET    /api/v1/admin/model-metrics  -> real stored metadata.json fields for each of the 6 trained
                                        models' currently-pinned version (Phase 8) — never a live
                                        drift computation (that's Phase 14 scope)
GET    /api/v1/admin/system-health  -> a real DB SELECT 1, a real Redis PING, and key-table row
                                        counts. Deliberately NOT audit-log-based — audit_logs is
                                        Phase 15 scope (docs/SECURITY.md)
```
Every route requires `Depends(require_role(Role.ADMIN))` — 401 for no/invalid auth, 403 for an
authenticated user who isn't an admin. No Idempotency-Key/rate-limit on any of them — no LLM call
anywhere in this feature. The original sketch's separate `/admin/analytics`, `/admin/datasets`,
`/admin/models`, `/admin/system` routes are folded into `/admin/ai-usage` +
`/admin/model-metrics` + `/admin/system-health` (three, not four, since "datasets" here just
means the skill/job catalogs `/admin/skills` and `/admin/jobs` already manage) — the frontend
further consolidates ai-usage + model-metrics + system-health into one `/admin` overview page,
the same way Phase 12 consolidated its own "market intelligence" sections.

## 6. OpenAPI → shared types

FastAPI auto-generates `openapi.json`; a CI/dev script (`packages/types`) runs
`openapi-typescript` against it so `apps/web` consumes generated request/response types instead
of hand-maintained duplicates. Domain types that predate the backend (used for design work) live
in `packages/types/domain/` and are reconciled with generated types once endpoints exist.

## 7. Streaming responses

Neither RAG (`POST /api/v1/rag/query`, Phase 9) nor interview-answer evaluation
(`POST /api/v1/interviews/{id}/answer`, Phase 11) actually streams — this section originally
sketched both as Server-Sent Events, but each shipped instead as a single non-streaming JSON
response for the same reason: real Idempotency-Key reserve/replay and real per-user rate-limiting
are far simpler to build correctly against one atomic response than against a stream that would
need to be cached and replayed chunk-by-chunk, and both phases' mandate was to build those
controls for real rather than defer them again (see §"RAG / AI chat" and §"Interviews" above for
each one's own note). `LLMProvider.stream()` (`app/ai/llm/base.py`) exists in the provider
abstraction but has zero real consumers anywhere in the codebase — infrastructure kept ready for
a genuine future streaming use case (e.g. a longer-form answer format where non-streaming latency
becomes a real problem), not a broken promise this doc forgot to update. If a future phase adds
real streaming, SSE is still the intended transport: each event a typed JSON payload
(`{"type": "token" | "source" | "done" | "error", ...}`), not raw provider output, so the
frontend never depends on a specific LLM provider's stream shape.
