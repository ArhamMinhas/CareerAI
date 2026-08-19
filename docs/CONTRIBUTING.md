# Contributing to CareerAI

This is currently a single-maintainer, phase-driven build (see [ROADMAP.md](./ROADMAP.md)).
This document describes the workflow once Phase 1 (project foundation) lands tooling; today,
in Phase 0, only documentation and the repository skeleton exist.

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

```bash
cp .env.example .env          # fill in required values
docker compose -f infrastructure/docker/docker-compose.yml up
```

Frontend: `apps/web` (Next.js dev server, hot reload). Backend: `apps/api` (FastAPI,
`--reload`). Worker: `apps/worker` (Celery, autoreload in dev). Migrations:
`alembic upgrade head` run against the local Postgres container.

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
