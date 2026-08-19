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

**Not yet done (expected — later phases):** no real Supabase project is connected yet (the
`SUPABASE_*` env vars are blank in a fresh checkout by design — see
[CONTRIBUTING.md §2](./CONTRIBUTING.md#2-local-setup-from-phase-1-onward)); until a developer
fills those in, auth-dependent behavior simply doesn't activate rather than erroring.

## Phase 2 — Premium Frontend ⬜

Landing page (all sections per spec §10), navigation, dashboard shell, responsive layout,
dark/light theme, Framer Motion + GSAP + Lenis wiring, 3D hero (with fallback per
[UI_ARCHITECTURE.md §6](./UI_ARCHITECTURE.md#6-3d-strategy)), mobile UI, and the technical SEO
foundation from [SEO.md §2](./SEO.md#2-technical-seo-implementation-nextjs-app-router)
(metadata API, robots.txt, sitemap scaffold, JSON-LD for `/`).

## Phase 3 — User / Profile System ⬜

Profile, education, experience, projects, skills (manual entry), career goals — CRUD UI + API.

## Phase 4 — Resume Intelligence ⬜

Upload (PDF/DOCX), async processing pipeline, deterministic + NLP + LLM extraction, resume
scoring ([ML_PIPELINE.md §2.1](./ML_PIPELINE.md#21-resume-score)), resume visualization.

## Phase 5 — AI Infrastructure ⬜

LLM provider abstraction, embeddings, pgvector wiring, prompt management, AI pipeline
scaffolding, structured-output validation, `ai_conversations` logging — per
[AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md).

## Phase 6 — Skill Gap Engine ⬜

Skill taxonomy, career skill profiles (`career_paths` table), gap comparison, recommendations,
visualizations. Also ships the public, SEO-indexable `/careers/[slug]` and `/skills/[slug]`
pages ([SEO.md §1](./SEO.md#1-what-gets-indexed-vs-what-doesnt)) — these render the same curated
role/skill data the gap engine uses internally, so the content is authored once.

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
