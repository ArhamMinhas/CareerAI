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

## Phase 1 — Project Foundation ⬜

Monorepo tooling (workspaces), Next.js app bootstrap, FastAPI app bootstrap, PostgreSQL +
pgvector via Docker Compose, Alembic baseline migration (`users`, `profiles` tables),
Supabase Auth wiring, Docker images, base CI (lint/type/test), starter design tokens.

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

Skill taxonomy, career skill profiles, gap comparison, recommendations, visualizations.

## Phase 7 — Job Recommendation ⬜

Job database + ingestion, semantic search, hybrid recommendation/ranking
([ML_PIPELINE.md §2.2](./ML_PIPELINE.md#22-job-match-score)), `/jobs/[id]` pages — this is also
when the programmatic-SEO surface from [SEO.md §2.3](./SEO.md#23-sitemap-appsitemapts) and
`JobPosting` structured data go live.

## Phase 8 — Data Science ⬜

`ml/` dataset pipeline, EDA notebooks, feature engineering, skill-demand analysis, clustering,
the six predictive models in [ML_PIPELINE.md §3](./ML_PIPELINE.md#3-trained-ml-models),
evaluation against baselines.

## Phase 9 — RAG ⬜

Knowledge base ingestion/chunking, embeddings, retrieval, grounded generation with source
citations — per [AI_ARCHITECTURE.md §6](./AI_ARCHITECTURE.md#6-rag-pipeline).

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

## Phase 16 — Deployment ⬜

Production deploy of web/API/worker/Redis/DB, DNS/HTTPS, environment configuration, monitoring,
CI/CD promotion pipeline, and the SEO go-live checklist in
[DEPLOYMENT.md §6](./DEPLOYMENT.md#6-domain-https-and-seo-go-live-checklist) (Search Console,
Bing Webmaster, sitemap submission).

## Definition of Done

A phase is complete only when (spec §58): implementation actually works, types pass, lint
passes, tests pass, the app builds, responsive UI works, errors are handled (loading/success/
empty/error/retry states), documentation is updated, new environment variables are documented
in `.env.example`, and no obvious console errors remain.
