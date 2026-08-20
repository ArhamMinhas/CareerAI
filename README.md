# CareerAI — AI Career Intelligence & Recruitment Platform

CareerAI is an AI-powered career intelligence platform: users upload a resume, target a career,
and get a structured analysis — resume scoring, skill-gap detection, job matching, a
personalized learning roadmap, AI mock interviews, and career/job-market analytics — built on a
combination of deterministic algorithms, trained ML models, retrieval (RAG), and LLM reasoning,
never a bare "ask the LLM for everything" wrapper.

**Status: Phase 3 — User / Profile System ✅.** Monorepo, Next.js 16 + FastAPI apps, PostgreSQL +
pgvector via Docker Compose, base CI, the full landing page/dashboard shell/3D hero/theme/SEO
plumbing from Phase 2, and now real auth (email/password sign-in/up, route-gated dashboard) plus
a full profile system — education, experience, projects, skills, career goals — with CRUD UI and
API. See [docs/ROADMAP.md](docs/ROADMAP.md) for the full phase-by-phase status.

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
│   ├── api/             FastAPI backend (layered: api/core/models/schemas/services/repositories/ai/ml/workers)
│   └── worker/          Celery worker
├── packages/
│   ├── ui/               shared component library
│   ├── types/             shared TypeScript types
│   └── config/             shared lint/tsconfig/tailwind config
├── ai/                   standalone AI service layer (pipelines, prompts, agents, embeddings, evaluation)
├── ml/                   data science pipeline (data, features, models, notebooks, training)
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
