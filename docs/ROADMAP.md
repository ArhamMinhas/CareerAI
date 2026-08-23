# CareerAI — Development Roadmap

Phases are implemented strictly one at a time, on request (spec §56) — "Start Phase 1" builds
only Phase 1. This document tracks scope and status per phase.

## Status legend

✅ Complete · 🚧 In progress · ⬜ Not started

## Phase 0 — Architecture ✅

Repository skeleton, database design, API design, AI architecture, ML architecture, UI
architecture, SEO strategy, security model, deployment plan, and this roadmap. No application
code. **Deliverables:** [ARCHITECTURE.md](./ARCHITECTURE.md), [DATABASE.md](./DATABASE.md),
[API.md](./API.md), [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md), [ML_PIPELINE.md](./ML_PIPELINE.md),
[UI_ARCHITECTURE.md](./UI_ARCHITECTURE.md), [SEO.md](./SEO.md), [SECURITY.md](./SECURITY.md),
[DEPLOYMENT.md](./DEPLOYMENT.md), [CONTRIBUTING.md](./CONTRIBUTING.md), monorepo directory
skeleton, `.env.example`.

## Phase 1 — Project Foundation ✅

Monorepo tooling (npm workspaces), Next.js 16 app bootstrap (App Router, TypeScript, Tailwind
v4), FastAPI app bootstrap (layered `app/` package, request-ID middleware, standard
success/error envelopes per [API.md](./API.md)), PostgreSQL + pgvector via Docker Compose
(verified live — `CREATE EXTENSION vector` confirmed), Alembic baseline migration (`users`,
`profiles` tables, applied and drift-checked), Supabase Auth wiring (JWT verification
dependency + frontend `@supabase/ssr` client/server/proxy helpers — degrades gracefully when
unconfigured rather than crashing, per spec §57), Docker images for web/api/worker (dev +
production multi-stage), base CI ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml):
lint/typecheck/test for both apps, Postgres+Redis service containers), starter design tokens
([packages/config/tailwind-tokens.css](../packages/config/tailwind-tokens.css)).

**Verified locally end-to-end:** `docker compose up` brings up all 5 services; `GET
/api/v1/health` and `GET /api/v1/auth/me` (401 when unauthenticated) respond correctly through
the mapped ports; the web homepage renders and its "Check API health" link resolves against the
live API; lint/typecheck/test/build are clean for both apps; `alembic check` reports no drift
against the ORM models.

**Update:** a real Supabase project is now connected and verified end-to-end (real user →
issued JWT → `/api/v1/auth/me` → correct local `users` row). That project turned out to use
current-generation asymmetric JWT Signing Keys (ES256) rather than the legacy HS256 shared
secret Phase 1 assumed — `_decode_supabase_jwt` now routes by the token's own `alg` header to
whichever verification path applies (`apps/api/app/core/security.py`), with regression tests
for both. `NEXT_PUBLIC_SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY` were also renamed to
`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`/`SUPABASE_SECRET_KEY` to match Supabase's current
naming. A fresh checkout with `SUPABASE_*` still blank continues to degrade gracefully rather
than erroring — see [CONTRIBUTING.md §2](./CONTRIBUTING.md#2-local-setup-from-phase-1-onward).

## Phase 2 — Premium Frontend ✅

Landing page, navigation, dashboard shell, responsive layout, dark/light theme, Framer Motion
(`motion/react`) + GSAP/ScrollTrigger + Lenis wiring, a 3D hero (React Three Fiber skill/career
network with a 2D SVG fallback — capability-gated via `useSyncExternalStore`, not an
effect-driven check, per [UI_ARCHITECTURE.md §6](./UI_ARCHITECTURE.md#6-3d-strategy)), mobile
UI (bottom nav in the dashboard shell, single-column landing collapse), and the technical SEO
foundation from [SEO.md §2](./SEO.md#2-technical-seo-implementation-nextjs-app-router)
(metadata API, `robots.ts`, `sitemap.ts`, JSON-LD `Organization`/`WebSite`/`FAQPage` on `/`).

**Content composition deviates from spec §10's literal 16-section list, deliberately:** the
five core-capability sections (resume intelligence, skill gaps, job matching, AI interview,
career roadmap) are one bento-grid "product tour" instead of five near-identical stacked
sections, and market-intelligence + analytics share one section with a real Recharts chart.
All required content is present; the composition avoids the repetition an anti-generic-design
pass would otherwise flag. 11 visually distinct sections instead of 16 mechanically similar
ones.

**Architecture note:** `packages/ui` is still just a README — component primitives
(`Button`, `Container`, `Section`, `Accordion`, `EmptyState`, ...) live in
`apps/web/components/ui` instead. There's only one consumer app right now, so extracting a
formally separate shared package would add cross-package build/resolution complexity with no
current benefit; revisit once a second app (e.g. an admin surface) actually needs to share
these.

**Verified visually, not just via lint/typecheck/test/build:** real end-to-end Chromium
(Playwright) checks in both themes and at mobile width, with a simulated scroll pass since the
scroll-reveal animations (`whileInView`) only trigger on real scroll — a naive full-page
screenshot tool without that simulation reads as blank, which is expected `whileInView`
behavior, not a bug. Zero console errors/hydration warnings on a clean server start.

## Phase 3 — User / Profile System ✅

Profile, education, experience, projects, skills (manual entry), career goals — CRUD UI + API,
plus the email/password auth pages this phase needed to actually exercise it (`/sign-in`,
`/sign-up`, dashboard route guard) — flagged as Phase 3 work in `proxy.ts`'s own comment back
in Phase 1, since `proxy.ts` only refreshes the session cookie, it never gated a route.

**Backend:** `education`, `experience`, `projects`, `skills`, `user_skills`, `career_goals`
tables (Alembic migration `994aa88465af`). `education`/`experience`/`projects` use soft delete
(`deleted_at`, docs/DATABASE.md §1); `user_skills`/`career_goals` are hard-deleted — they're
join-like/preference rows, not durable content. Routes: `GET`/`PATCH /profile` (lazily creates
the `Profile` row on first touch, same pattern `get_current_user` already used for `users`);
full CRUD under `/profile/education`, `/profile/experience`, `/profile/projects`,
`/profile/skills` (all scoped to the caller's own profile — a mismatched id 404s rather than
403s, so ownership isn't leaked); full CRUD on `/career-goals`; `GET /skills?q=` for the
manual-entry autocomplete (get-or-create by name, not the full taxonomy browse/gap-analysis
surface — that's Phase 6).

**Frontend:** `/sign-in`, `/sign-up` (Supabase email/password only — Google OAuth from
docs/SECURITY.md is deferred, since it needs provider credentials configured in the Supabase
project that don't exist yet); `app/dashboard/layout.tsx` now redirects to `/sign-in` server-
side (`getUser()`, not `getSession()`, since it decides whether to render the authenticated
shell at all) when unauthenticated; `/dashboard/profile` — basic info, career goals,
experience, education, projects, skills, each with real loading/empty/error-with-retry states
and the established hover/motion design system.

**Real bug found and fixed during verification:** the frontend's `apiFetch` helper called
`createClient()` (a fresh Supabase browser client) on every single request. The profile page
fires 6 parallel requests via `Promise.all`, and under real browser concurrency (not
reproducible with curl or a bare `Promise.all` of `fetch` — both lack the multiple client
instances), separate freshly-initializing client instances raced on session state and some
sent no/stale auth, surfacing as genuine 401s. Fixed with a single shared client instance
(`apps/web/lib/api.ts`).

**Verified end-to-end**, not just via lint/typecheck/test/build: a real Supabase user created
via the Admin API, signed in through the actual `/sign-in` form (not a mocked session), full
CRUD exercised through the real UI for every sub-resource, data confirmed present after a hard
reload, sign-out confirmed, and the unauthenticated `/dashboard` redirect confirmed — in both
themes, zero console errors.

## Phase 4 — Resume Intelligence ✅

Upload (PDF/DOCX), async processing pipeline, deterministic + NLP + LLM extraction, resume
scoring ([ML_PIPELINE.md §2.1](./ML_PIPELINE.md#21-resume-score)), resume visualization. Also
shipped Google OAuth (`GoogleButton` + `/auth/callback`), completing the auth surface Phase 3
started with email/password only.

**Backend:** `resumes`/`resume_versions` tables (soft-deleted per docs/DATABASE.md §1 — spec
explicitly names `resumes` as a soft-delete table). `POST /resumes/upload` streams the file to
Supabase Storage (`app/core/storage.py`, private bucket + signed download URLs — resumes are
personal documents, never a public URL) and enqueues `resumes.process`, a Celery task
(`app/workers/resume_tasks.py`) that: extracts text (`pypdf`/`python-docx`), detects standard
section headers via regex/keyword matching (`app/services/resume_parsing.py` — a
dependency-light stand-in for the spaCy pass docs/AI_ARCHITECTURE.md describes, not a trained
model, per ML_PIPELINE.md §1's "baseline first"), runs LLM structured extraction
(`app/ai/resume_extraction.py` — one direct, schema-constrained OpenAI call, deliberately
**not** the full provider abstraction docs/AI_ARCHITECTURE.md §2 describes, since that's
Phase 5's job and Phase 4 needed extraction working now), computes the deterministic
`ScoreBreakdown` from ML_PIPELINE.md §2.1's exact formula (`app/services/resume_scoring.py`,
every sub-score carries `{score, explanation, evidence}`), and additively syncs extracted
skills into `user_skills` with `source=resume` — the integration point Phase 3's `UserSkill`
model docstring had already anticipated.

**Frontend:** `/dashboard/resume` — drag-and-drop upload, a status-polling list (queued /
analyzing / analyzed / failed), and a score breakdown view (expandable explanations + evidence
per sub-score, extracted skills/experience/education/projects, download/re-analyze/delete).
The dashboard home's "Resume score" card now shows the real latest score instead of a
placeholder.

**Two real bugs found and fixed during end-to-end verification** (both only reproduce under
real infrastructure, not unit tests or curl):
- `celery_app.py`'s `autodiscover_tasks(["app.workers"])` silently registered nothing — Celery
  autodiscovery only ever imports a module literally named `tasks.py` inside each package,
  never arbitrarily-named ones like `resume_tasks.py`. Fixed with an explicit
  `include=["app.workers.resume_tasks"]` on the `Celery()` constructor, which works regardless
  of filename and stays legible as more task modules are added.
- `_decode_supabase_jwt` (`app/core/security.py`) had no `leeway` on `jwt.decode()`. A token
  used within ~1-2s of being freshly issued by `signInWithPassword` was intermittently
  rejected, then succeeded seconds later with the *same* token — a clock-skew signature between
  the token issuer (Supabase's servers) and this verifier (a different machine). Fixed with
  `leeway=30`, standard practice for any two-machine JWT setup.

**Known gap, explicit scope decision:** `POST /resumes/{id}/analyze`'s `Idempotency-Key` is
required and enforced against concurrent re-analysis of the *same* resume (409 if already
processing), but isn't backed by a persistent idempotency-key cache/store — a client retry with
a fresh key after a completed response could still trigger a second real analysis. Full
idempotency-key infrastructure is a fast-follow, not blocking for this phase.

## Phase 5 — AI Infrastructure ✅

LLM provider abstraction, embeddings, pgvector wiring, prompt management, structured-output
validation, `ai_conversations` logging — per [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md). Also
wired the dashboard's 3D skill constellation to real profile skill data, replacing the
decorative placeholder from Phase 2.

**Deliberate scope deviation from AI_ARCHITECTURE.md §2:** that doc describes a top-level `ai/`
package with `apps/api/app/ai/` as a thin adapter, for cross-package importability from future
notebooks/`ml/` code. Built entirely inside `apps/api/app/ai/` instead — no `ml/` package or
notebooks exist yet to justify it, the only current consumers (the FastAPI API and the Celery
worker) already share this exact codebase and Docker image, and a real top-level package would
need Docker `COPY`/`PYTHONPATH` changes for zero present benefit. Same reasoning already applied
to `packages/ui` staying a stub since Phase 2 — revisit when a second, genuinely separate
consumer (e.g. a notebook or standalone ML job) actually exists.

**Provider abstraction** (`app/ai/llm/`): `LLMProvider` protocol (`complete`/`stream`/`embed`)
with `OpenAIProvider` and `GeminiProvider` implementations and a `router.py` that resolves
`(provider, model)` per named task from `settings.llm_provider`/`llm_model_default`/
`llm_model_reasoning` — switching providers or routing a task to a cheaper/stronger model is an
env var change, not a code change. Both providers use their vendor's native structured-output
mode (OpenAI `chat.completions.parse()`, Gemini `response_schema`) and re-validate against the
given Pydantic model with one bounded retry (validation error fed back into the prompt) before
raising a typed `AIExtractionError`, per §3. `app/ai/resume_extraction.py` — the Phase 4
stopgap that called `openai` directly — is migrated onto this abstraction, retiring the
exception AI_ARCHITECTURE.md §2 had flagged for it.

**Prompt management** (`app/ai/prompts/`): versioned `.md` files (system instructions below a
`---` metadata header) loaded by `(name, version)` via a small cached registry, starting with
`resume_extraction/v1.md` (moved out of the Python module it used to live inline in).

**Embeddings & pgvector** (`app/models/embedding.py`, `app/services/embeddings.py`): the
polymorphic `embeddings` table from [DATABASE.md §2.2](./DATABASE.md#22-resume-intelligence)
with a `vector(1536)` column and an HNSW/cosine index (pgvector extension itself already
provisioned since Phase 1 via `infrastructure/docker/postgres-init/001-extensions.sql`, not an
Alembic migration). `embed_text()` caches by content hash in Redis before calling the provider
so re-embedding identical content (e.g. re-uploading an unchanged resume) never re-calls the
API; a cache failure degrades to calling the provider directly rather than blocking the caller.
The resume pipeline now embeds each resume's full text on every analysis.

**`ai_conversations` logging** (`app/models/ai_conversation.py`,
`app/services/ai_conversations.py`): every LLM call the resume pipeline makes is logged with
model, token counts, and latency; `request_meta` holds only the prompt name/version, never full
prompt/response text or raw PII, per §10's safe-logging policy. `feature` is plain text, not a
DB enum — validated at the application layer (`AIFeature`) instead, since new AI features land
every phase and a Postgres enum would need a migration for each one.

**Verified locally end-to-end:** ruff/mypy/pytest clean (62 tests, including new coverage for
both providers' retry/error-wrapping behavior, the router, the prompt registry, and
conversation/embedding persistence); `alembic check` reports no drift; a real resume re-analysis
through the rebuilt Docker stack produced a real score plus a real `ai_conversations` row and a
real `embeddings` row.

## Phase 6 — Skill Gap Engine ✅

Skill taxonomy extended (`skills.synonyms`/`seo_summary`/`embedding`), curated career-path
catalog (`career_paths`/`career_path_skills`), deterministic gap comparison, recommendations,
and a new dashboard visualization. Ships the public, SEO-indexable `/careers`, `/careers/[slug]`,
and `/skills/[slug]` pages ([SEO.md §1](./SEO.md#1-what-gets-indexed-vs-what-doesnt)) — these
render the same curated role/skill data the gap engine uses internally, so the content is
authored once.

**Backend:** `career_paths`/`career_path_skills`/`skill_gaps` tables plus `skills.synonyms`/
`seo_summary`/`embedding` (Alembic migration, HNSW cosine indexes on both new embedding
columns, matching Phase 5's `embeddings` table pattern). `app/services/skill_gap.py` is pure
deterministic set comparison — no LLM call (docs/AI_ARCHITECTURE.md §1) — diffing a user's
`user_skills` against a resolved career path's required-skill profile; priority is
`career_path_skills.weight` (doubled if `is_core`, doubled again for missing vs. weak) since
`skill_demand` doesn't exist until Phase 7/8 (see docs/ML_PIPELINE.md §2.3's implementation
note). `GET /skills/gaps` auto-computes and caches on first read (mirrors resume analysis);
`POST /skills/gaps/refresh` forces recomputation after a profile change. `GET /careers`,
`GET /careers/{slug}`, `GET /skills/{id_or_slug}`, and `GET /skills/curated` are public,
unauthenticated routes backing the SSG pages and sitemap. `app/scripts/seed_career_paths.py`
seeds 8 real, curated career paths (AI Engineer, ML Engineer, Data Scientist, Backend/Frontend/
Full-Stack Engineer, DevOps Engineer, Product Manager) and backfills `seo_summary`/`embedding`
for 20 common skills, using Phase 5's `embed_text()` for real OpenAI embeddings — idempotent,
re-runnable, not part of CI (it makes real paid API calls; CI's tests are fully self-contained
fixtures, never dependent on seeded data).

**Frontend:** `/careers` (index) and `/careers/[slug]` (detail: description, required-skill
list sorted by weight with core badges, related career paths via embedding similarity) —
true SSG via `generateStaticParams`, ISR revalidate 1h. `/skills/[slug]` (seo_summary,
synonyms, related skills, cross-links to career paths that require it) — same SSG/ISR
strategy. `sitemap.ts` now includes both; `BreadcrumbList` (careers, skills) and `DefinedTerm`
(skills) JSON-LD per docs/SEO.md §2.4 — `Organization` JSON-LD was hoisted from the landing
page into the root layout so it's genuinely site-wide as that section always specified, not
landing-page-only. New `/dashboard/skill-gap` view: target-role selector, animated summary
tiles/recommended-next list/full breakdown (Motion, staggered reveal, color-coded by gap
level), plus a real `SkillGapCard` on the dashboard home replacing the old static placeholder.

**Real bug found and fixed during live verification** (present since Phase 1, first surfaced
by Phase 6's dashboard adding more concurrent first-load API calls): `get_current_user`
(app/core/security.py) selected-then-inserted a user's local `users` row on their very first
authenticated request with no protection against concurrent duplicate-insert races. A fresh
sign-in's dashboard fires several `apiFetch` calls in parallel (each on its own DB session),
and more than one could reach the "row doesn't exist yet" branch before either committed — the
loser crashed with a duplicate-key `IntegrityError`, which the browser reported as a
misleading "blocked by CORS policy" error (Chrome misreports a response that never completed
as a CORS failure) rather than a clear 500. Fixed with the same SAVEPOINT-and-retry pattern
already used for `get_or_create_skill` (app/services/skill_taxonomy.py) — a regression test
reproduces the concurrent race directly.

**Two more real bugs found via a self-review pass** (`/code-review`) after the above,
before this was considered done:
- `compute_and_store_skill_gaps` (app/services/skill_gap.py) had the *exact same* class of
  race as `get_current_user` above, in its own delete-then-insert of `skill_gaps` rows — two
  concurrent computations for the same user+career-path (GET's auto-compute racing a POST
  `/refresh`, say) could both see "no rows yet" and collide on insert. Same SAVEPOINT fix;
  since the computation is deterministic, the loser just reads back the winner's equivalent
  result instead of retrying its own write.
- `resolve_career_path` (app/services/career_paths.py) passed the raw, caller-controlled
  `target_role` straight into an `ILIKE` pattern for its title-fallback match. `%`/`_` in that
  string are wildcards to `ILIKE`, not literal characters — a bare `%` matches every published
  career path, which crashed `scalar_one_or_none()` with `MultipleResultsFound` (an unhandled
  500) instead of cleanly resolving to "not found." Fixed by switching to a plain case-folded
  equality comparison, which is also what the fallback was always semantically meant to be
  (an exact, case-insensitive title match, not a substring/wildcard search).

Also fixed in the same pass: `compute_and_store_skill_gaps` was being handed a raw
`target_role` string and re-resolving it internally, even though every caller already
resolves the `CareerPath` for its own response — a wasted duplicate query on every
cache-miss/refresh, removed by threading the already-resolved `CareerPath` through instead.

**Deliberate scope decisions:** `Occupation` JSON-LD for career pages and dynamic
`opengraph-image` generation are both explicitly flagged in docs/SEO.md as incremental
enhancements, not launch blockers — deferred, along with a shared OG-image template that makes
more sense once jobs/companies pages also exist (Phase 7). `skill_demand` (docs/DATABASE.md
§2.5) needs aggregated real job postings to be meaningful, so it's not built yet either — see
the ML_PIPELINE.md note on the interim priority formula. Also fixed in passing: a real
production Docker gap where server-side (SSR/SSG) fetches from inside the web container need
a different API URL (`API_INTERNAL_URL=http://api:8000`, the Docker network's service name)
than the browser does (`NEXT_PUBLIC_API_URL=http://localhost:8000`, the published port) —
`lib/public-api.ts` and `docker-compose.yml` now distinguish the two. The equivalent fix for a
non-Compose production Docker build (passing these as build ARGs to `Dockerfile.web`, since a
standalone `docker build` has no compose-level env injection) is left for Phase 16/17
(Deployment) rather than guessed at now.

**Verified locally end-to-end:** ruff/mypy/pytest clean (79 tests — including two live
concurrency regression tests — both with real and blank AI provider keys, matching CI);
`alembic check` reports no drift; frontend lint/typecheck/test/build all clean, including
`generateStaticParams` actually pre-rendering all 8 career paths and 20 curated skills at
build time. Real Playwright verification against the rebuilt Docker stack: a fresh throwaway
Supabase user signing in, adding real skills through the actual profile UI, and seeing a
correctly color-coded, correctly-prioritized skill-gap breakdown for a real target role;
`/careers`, `/careers/[slug]`, and `/skills/[slug]` rendering real seeded content with working
cross-links in both directions.

## Phase 7 — Job Recommendation ⬜

Job database + ingestion, semantic search, hybrid recommendation/ranking
([ML_PIPELINE.md §2.2](./ML_PIPELINE.md#22-job-match-score)), `/jobs/[id]` and `/companies/[id]`
pages — this is also when the programmatic-SEO surface from
[SEO.md §2.3](./SEO.md#23-sitemap-appsitemapts) and `JobPosting`/`Organization` structured data
go live.

## Phase 8 — Data Science ⬜

`ml/` dataset pipeline, EDA notebooks, feature engineering, skill-demand analysis, clustering,
the six predictive models in [ML_PIPELINE.md §3](./ML_PIPELINE.md#3-trained-ml-models),
evaluation against baselines.

## Phase 9 — RAG ⬜

Knowledge base ingestion/chunking, embeddings, retrieval, grounded generation with source
citations — per [AI_ARCHITECTURE.md §6](./AI_ARCHITECTURE.md#6-rag-pipeline). The same
`resources` content table doubles as the public, SEO-indexable `/resources/[slug]` article
pages — one content source, two consumers (RAG grounding + organic search).

## Phase 10 — Learning Roadmap ⬜

Personalized roadmap generation, prerequisite sequencing, resources, project suggestions,
progress tracking.

## Phase 11 — AI Interview ⬜

Interview generation, session flow, answer evaluation, scoring, feedback, history, analytics —
per [AI_ARCHITECTURE.md §8](./AI_ARCHITECTURE.md#8-agents) (Interview Agent).

## Phase 12 — Career Analytics ⬜

Skill trends, job trends, salary analytics, career analytics, candidate analytics dashboards.

## Phase 13 — Admin ⬜

Admin dashboard, user management, dataset management, job management, AI usage monitoring,
model monitoring.

## Phase 14 — MLOps ⬜

Model versioning/registry, inference API hardening, evaluation pipeline automation, drift
monitoring, retraining workflow — per [ML_PIPELINE.md §6](./ML_PIPELINE.md#6-model-registry--versioning-mlops-phase-14).

## Phase 15 — Production Hardening ⬜

Full OWASP pass, rate limiting, caching, performance/Core Web Vitals budgets (incl. the
Lighthouse CI gate from [SEO.md §4](./SEO.md#4-core-web-vitals--performance-as-a-ranking-factor)),
accessibility audit, full test coverage of critical flows, logging/error-handling completeness.

## Phase 16 — Deployment (Initial) ⬜

First real deployment, optimized for getting a working production URL quickly rather than
final scale: `apps/web` on Vercel, `apps/api`/`apps/worker` on Railway (or AWS ECS/Fargate
directly if that's not meaningfully slower to stand up), Supabase for Postgres+pgvector+Auth,
Upstash Redis, GitHub Actions CI/CD promoting `main` → staging → production, custom domain +
HTTPS, and the baseline SEO go-live checklist in
[DEPLOYMENT.md §6](./DEPLOYMENT.md#6-domain-https-and-seo-go-live-checklist) (canonical domain,
Search Console + Bing Webmaster verification, sitemap submission). This phase proves the whole
pipeline works end-to-end in the cloud.

## Phase 17 — Cloud + SEO + Production Deployment ⬜

Hardens Phase 16 into the target production architecture in
[ARCHITECTURE.md §6](./ARCHITECTURE.md#6-deployment-topology) and closes out the full SEO spec,
rather than the baseline subset shipped in Phase 2/7/16:

- **Cloud infrastructure:** migrate `apps/api`/`apps/worker`/ML inference off Railway onto AWS
  ECS/Fargate (autoscaling task definitions, private VPC networking to Supabase/Upstash),
  Vercel CDN/edge config tuned, custom domain + SSL fully automated (no manual cert steps),
  infrastructure-as-code for the ECS stack rather than console-clicked resources.
- **SEO — full rollout:** every public route type live and validated —
  `/`, `/careers`, `/careers/[slug]`, `/skills/[slug]`, `/jobs`, `/jobs/[id]`, `/companies/[id]`,
  `/resources/[slug]` — each with SSR/SSG per [SEO.md §5](./SEO.md#5-rendering--freshness-strategy-for-indexable-routes),
  dynamic metadata, Open Graph + Twitter Cards, canonical URLs, `sitemap.xml`, `robots.txt`,
  `JobPosting`/`Organization`/`BreadcrumbList`/`FAQPage` JSON-LD, semantic HTML with correct
  heading hierarchy, WebP/AVIF images via `next/image`, and the internal-linking topic clusters
  in [SEO.md §3](./SEO.md#3-on-page--content-seo). Authenticated app routes (`/dashboard`,
  `/resume`, `/analytics`, `/interviews`, `/settings`, `/admin/*`) are confirmed `noindex` and
  excluded from the sitemap.
- **Core Web Vitals:** production Lighthouse CI budgets enforced on every public route (not just
  `/`), per [SEO.md §4](./SEO.md#4-core-web-vitals--performance-as-a-ranking-factor).
- **Monitoring & logging:** Sentry wired into `apps/web`, `apps/api`, and `apps/worker` for
  error tracking/release tracking; structured cloud logs (CloudWatch or platform-native)
  correlated by request ID; uptime + AI-cost alerting active.
- **Scaling:** ECS service autoscaling policies (CPU/queue-depth based for workers), Postgres
  connection pooling (PgBouncer/Supabase pooler) sized for expected load.
- **Production security:** WAF/rate limiting at the edge, secrets rotation policy, dependency
  and container image scanning in CI, final OWASP re-check against the live environment (not
  just the Phase 15 code-level pass).

This is the phase that turns "an AI application running locally" into a properly cloud-deployed,
SEO-discoverable production product.

## Definition of Done

A phase is complete only when (spec §58): implementation actually works, types pass, lint
passes, tests pass, the app builds, responsive UI works, errors are handled (loading/success/
empty/error/retry states), documentation is updated, new environment variables are documented
in `.env.example`, and no obvious console errors remain.
