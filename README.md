# CareerAI — AI Career Intelligence & Recruitment Platform

CareerAI is an AI-powered career intelligence platform: users upload a resume, target a career,
and get a structured analysis — resume scoring, skill-gap detection, job matching, a
personalized learning roadmap, AI mock interviews, and career/job-market analytics — built on a
combination of deterministic algorithms, trained ML models, retrieval (RAG), and LLM reasoning,
never a bare "ask the LLM for everything" wrapper.

**Status: Phase 13 — Admin ✅.** Monorepo, Next.js 15 + FastAPI apps, PostgreSQL +
pgvector via Docker Compose, CI, the landing page/dashboard/theme/SEO plumbing from Phase 2,
the profile system (education, experience, projects, skills, career goals) from Phase 3, email/
password + Google OAuth and real resume intelligence (async PDF/DOCX upload, NLP + LLM
extraction, deterministic explainable scoring) from Phase 4, a provider-agnostic LLM/embeddings
abstraction with `ai_conversations` cost logging from Phase 5, a curated career-path catalog with
deterministic skill-gap comparison from Phase 6, real job postings ingested from the
Adzuna Jobs API (with real external apply links), keyword-then-semantic job search with
relevance-ranked results, the hybrid `job_match_score` engine (`/dashboard/matches`) plus a
live per-job fit score on individual postings, and public SEO-indexed `/jobs`, `/jobs/[id]`,
`/companies/[slug]` pages from Phase 7, six trained ML models (job-suitability, career
recommendation, skill clustering, salary prediction, job-category classification, skill-demand
forecasting) evaluated against real baselines and wired live into `/dashboard/matches`,
`/careers/[slug]`, and `/skills/[slug]` from Phase 8, and now a full RAG pipeline — knowledge-base
chunking/embedding, retrieval-grounded generation with source citations, a real per-user Redis
rate limiter and Idempotency-Key dedup, and public `/resources`/`/resources/[slug]` article pages
that double as the RAG retrieval corpus (`/dashboard/ask`) — from Phase 9, and now a
personalized learning roadmap — deterministic prerequisite sequencing (a real topological sort,
never LLM-decided) over curated skill resources and project suggestions, progress tracking, and
one bounded LLM narrative call, at `/dashboard/roadmap` — from Phase 10, and now AI mock
interviews — a curated, embedding-ranked question bank across 6 modes (technical, behavioral, HR,
system design, ML, data science), turn-by-turn structured LLM evaluation against per-mode
rubrics, session history, and real analytics aggregates, at `/dashboard/interviews` — from
Phase 11, and now career analytics — a personalized dashboard rollup (resume score, skill gaps,
interview performance, roadmap progress, job-search funnel) plus real, catalog-wide market
intelligence (trending skills, job-posting and salary trends, trending career paths, a per-skill
demand/salary table), all deterministic SQL aggregation with zero new LLM calls, at
`/dashboard/analytics` — from Phase 12, and now a role-gated admin panel — user/job/skill
management (including real embedding computation on admin-created postings), AI usage monitoring
over the real `ai_conversations` cost log, and read-only surfacing of all 6 trained models' real
stored metrics, at `/admin` — from Phase 13. See [docs/ROADMAP.md](docs/ROADMAP.md) for the full
phase-by-phase status.

## Why this project exists

Built to demonstrate end-to-end capability across full-stack engineering, AI engineering, ML
engineering, and data science in a single coherent product — not a CRUD app and not a ChatGPT
wrapper. See [docs/ROADMAP.md](docs/ROADMAP.md) and the architecture docs below for how each
discipline shows up concretely.

## Documentation map

| Doc | Covers |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, component responsibilities, request flows, deployment topology, key decisions |
| [docs/DATABASE.md](docs/DATABASE.md) | Full relational schema, ERDs, indexing strategy |
| [docs/API.md](docs/API.md) | REST API conventions, error format, endpoint catalog |
| [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) | LLM provider abstraction, embeddings, RAG, agents, prompt management, evaluation, cost control |
| [docs/ML_PIPELINE.md](docs/ML_PIPELINE.md) | Deterministic scoring formulas, trained ML models, data science pipeline, MLOps |
| [docs/UI_ARCHITECTURE.md](docs/UI_ARCHITECTURE.md) | Frontend rendering strategy, design system, animation, 3D, responsive/accessibility |
| [docs/SEO.md](docs/SEO.md) | Technical + on-page SEO across the full public surface (careers, skills, jobs, companies, resources), structured data, sitemaps, Core Web Vitals, search-engine setup so the deployed site is actually discoverable |
| [docs/SECURITY.md](docs/SECURITY.md) | AuthN/Z, OWASP mitigations, secrets, audit logging, data privacy |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Environments, Docker, CI/CD, deployment targets, go-live checklist |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Local setup, workflow, code style, testing expectations |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phase-by-phase plan (0–17) and status |

## Technology stack

- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind CSS, Framer Motion, GSAP,
  React Three Fiber, Lenis, Recharts. Deployed on **Vercel**.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy/SQLModel, Alembic. Deployed on **Railway**
  initially, migrating to **AWS ECS/Fargate** in Phase 17.
- **Data:** PostgreSQL + pgvector and Auth on **Supabase**; **Upstash Redis** for cache + Celery
  broker; resume files on Supabase Storage (S3-compatible alternative available).
- **AI/ML:** provider-agnostic LLM abstraction (OpenAI/Gemini cloud APIs), embeddings + RAG,
  scikit-learn/XGBoost for trained models.
- **Infra:** Docker, GitHub Actions CI/CD, **Sentry** for error/release monitoring (Phase 17).

Full rationale for each choice: [docs/ARCHITECTURE.md §8](docs/ARCHITECTURE.md#8-key-architectural-decisions-adr-style-summary).
Concrete deployment targets and the Phase 16 → 17 migration path:
[docs/DEPLOYMENT.md §5](docs/DEPLOYMENT.md#5-deployment-targets).

## Repository structure

```
career-ai/
├── apps/
│   ├── web/            Next.js frontend
│   ├── api/             FastAPI backend (layered: api/core/models/schemas/services/ai/workers)
│   └── worker/          Celery worker (shares the api app's codebase/image)
├── packages/
│   ├── ui/               README stub — component primitives live in apps/web/components/ui
│   │                     until a second consumer app justifies extracting them (see its README)
│   ├── types/             shared TypeScript types
│   └── config/             shared lint/tsconfig/tailwind config
├── ai/                   README stub — LLM/embeddings live in apps/api/app/ai instead (see its
│                         README for why); revisit if a real standalone consumer shows up
├── ml/                   data science pipeline (data, features, models, notebooks, training) — Phase 8
├── infrastructure/       Docker + deployment config
├── docs/                 architecture, database, API, AI, ML, UI, SEO, security, deployment, contributing, roadmap
├── .env.example
└── README.md
```

Each directory has its own `README.md` explaining its purpose in more depth.

## Getting started

```bash
cp .env.example .env
docker compose -f infrastructure/docker/docker-compose.yml up -d
cd apps/api && alembic upgrade head
```

Then open `http://localhost:3000` (web) and `http://localhost:8000/docs` (API). Full setup
detail, running the backend outside Docker, and connecting Supabase Auth:
[docs/CONTRIBUTING.md §2](docs/CONTRIBUTING.md#2-local-setup-from-phase-1-onward).

## Building this project

Development proceeds one phase at a time, on explicit request — see
[docs/ROADMAP.md](docs/ROADMAP.md) for the full phase list and
[docs/CONTRIBUTING.md §1](docs/CONTRIBUTING.md#1-phase-discipline) for how each phase is run.
