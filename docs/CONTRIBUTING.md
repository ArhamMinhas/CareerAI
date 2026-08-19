# Contributing to CareerAI

This is currently a single-maintainer, phase-driven build (see [ROADMAP.md](./ROADMAP.md)).
Phase 1 (project foundation) has landed, so the workflow below is live, not aspirational.

## 1. Phase discipline

Work proceeds one phase at a time (spec §2, §56). Before starting a phase:

1. Read the relevant architecture doc(s) in `docs/` for that phase.
2. Inspect what already exists — don't re-derive or overwrite working code.
3. Implement only that phase's scope.
4. Run lint, type checks, and tests; fix failures before moving on.
5. Update documentation touched by the change.
6. Note what remains for the next phase.

A phase is not "done" because files exist — see the Definition of Done in
[ROADMAP.md](./ROADMAP.md#definition-of-done).

## 2. Local setup (from Phase 1 onward)

### 2.1 Everything via Docker Compose (recommended)

```bash
cp .env.example .env          # fill in real values — see §2.3 for Supabase
docker compose -f infrastructure/docker/docker-compose.yml up -d
```

This starts all five services: `postgres` (with `pgvector` enabled via
`infrastructure/docker/postgres-init/001-extensions.sql`), `redis`, `api` (FastAPI,
`--reload`), `worker` (Celery), and `web` (Next.js, hot reload). First run builds the images
(a couple of minutes); after that, `up -d` is seconds.

Then apply migrations once (from `apps/api`, against the containerized Postgres — see §2.2 for
the venv setup, or run it from inside the container: `docker compose -f
infrastructure/docker/docker-compose.yml exec api alembic upgrade head`):

```bash
cd apps/api && alembic upgrade head
```

Verify: `http://localhost:3000` (web) and `http://localhost:8000/api/v1/health` (API — should
return `{"data":{"status":"ok"},...}`) and `http://localhost:8000/docs` (OpenAPI docs).

### 2.2 Running `apps/api` outside Docker (faster iteration on the backend alone)

```bash
cd apps/api
python -m venv .venv
./.venv/Scripts/activate        # ./.venv/bin/activate on macOS/Linux
pip install -r requirements/dev.txt
docker compose -f ../../infrastructure/docker/docker-compose.yml up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload
```

Lint/format/typecheck/test:

```bash
ruff check . && ruff format --check . && mypy app && pytest
```

### 2.3 Supabase Auth setup

A fresh checkout runs fine with the `SUPABASE_*` variables blank — `proxy.ts` and the backend
JWT dependency degrade gracefully rather than erroring (spec §57) — but auth won't actually
authenticate anyone until you connect a real project:

1. Create a project at [supabase.com/dashboard](https://supabase.com/dashboard).
2. **Settings → API** → copy the Project URL into `SUPABASE_URL` and
   `NEXT_PUBLIC_SUPABASE_URL`, the `anon`/`public` key into `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
   and the `service_role` key into `SUPABASE_SERVICE_ROLE_KEY` (backend-only — never expose it
   to the frontend).
3. Same page, **JWT Settings** → copy the JWT Secret into `SUPABASE_JWT_SECRET`. If your
   project only shows asymmetric "JWT Signing Keys" (no plain secret field), the verification
   approach in `apps/api/app/core/security.py` (`_decode_supabase_jwt`, HS256 shared-secret)
   needs to switch to JWKS-based verification instead — flag it, don't guess.
4. Restart the `api`/`web` containers (or local dev servers) so the new env vars are picked up.

### 2.4 Root-level scripts (frontend only, from the repo root)

```bash
npm run dev:web / build:web / lint:web / typecheck:web / test:web
```

Backend equivalents are run from `apps/api` directly (§2.2) — there isn't a Python-workspace
concept to route them through the root `package.json`.

## 3. Branching & commits

- `main` is always deployable to staging.
- Feature branches: `phase-N/<short-description>` (e.g. `phase-4/resume-upload-endpoint`).
- Commit messages describe *why*, not just *what*; one logical change per commit where
  practical.

## 4. Code style

- **TypeScript/React:** ESLint + Prettier (shared config in `packages/config`); strict
  `tsconfig`; no `any` without a comment explaining why.
- **Python:** Ruff (lint + format), mypy for type checking, `black`-compatible formatting.
- Follow the layering rules in [ARCHITECTURE.md §4](./ARCHITECTURE.md#4-backend-layering-appsapi)
  — no business logic in route handlers, no raw SQL outside repositories, no inline LLM calls
  outside the `ai/` layer.

## 5. Testing expectations

Every feature PR includes tests appropriate to what changed (spec §45):

- Backend: Pytest unit tests for services, integration tests for API routes against a test DB.
- Frontend: Vitest component tests for non-trivial components.
- AI changes (new/edited prompts or pipelines): a matching case added to `ai/evaluation/`.
- Critical user flows (register, upload resume, analyze, view gaps, generate roadmap, find
  jobs, run an interview) are covered by Playwright E2E tests once those flows exist.

## 6. Pull requests

Even in a single-maintainer workflow, changes are reviewed via PR (self-review checklist) so CI
runs before merge: lint, type check, unit + integration tests, build, and the AI evaluation gate
where applicable (see [DEPLOYMENT.md §4](./DEPLOYMENT.md#4-ci-pipeline-github-actions)).

## 7. Adding a dependency

Explain why before adding (spec §57): what problem it solves, why the existing stack can't, and
confirm it doesn't duplicate something already in use.

## 8. Adding an environment variable

Add it to `.env.example` with a comment explaining its purpose (spec §48), wire it into the
Pydantic `Settings` validation so missing-required-value failures happen at startup, and note it
in the relevant doc (e.g. new AI provider → [AI_ARCHITECTURE.md](./AI_ARCHITECTURE.md); new SEO
var → [SEO.md §7](./SEO.md#7-environment-variables)).
