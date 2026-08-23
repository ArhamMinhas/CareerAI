# CareerAI — CI/CD Pipeline

## Overview

The CI/CD pipeline is built on **GitHub Actions** and enforces code quality, security, and deployment standards across the monorepo.

### Key Principles

1. **Fail fast** — linting and type checks run first; tests follow; builds only happen if all quality gates pass
2. **Security first** — dependency scanning, secret detection, and vulnerability analysis run automatically
3. **Deterministic deployments** — Docker images are built once and promoted through environments (no rebuilds)
4. **Staging gates production** — all changes go to staging first; production deployments are manual and require approval

---

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:** Push to `main`/`master`, all pull requests

**Jobs:**

#### `web` (Next.js)
- Installs dependencies (cached)
- Runs ESLint
- Runs TypeScript type check
- Runs Vitest unit tests
- Builds the Next.js app

**Skipped:** Only runs if changes touch `apps/web/`, `package.json`, or `package-lock.json`

#### `api` (FastAPI)
- Spins up test PostgreSQL (pgvector) and Redis containers
- Installs dependencies (cached)
- Enables pgvector extension
- Runs Ruff linter and formatter checks
- Runs mypy type checker
- Runs Alembic migrations
- Runs pytest suite

**Environment:** All tests run against actual dev database; services are healthy before tests start

#### `security`
- **Trivy filesystem scan** — detects known CVEs in dependencies
- **npm audit** — checks frontend dependencies for vulnerabilities
- Results uploaded to GitHub Security tab (SARIF format)

**Severity threshold:** CRITICAL and HIGH vulnerabilities fail the build; MEDIUM are warnings

#### `build-images`
- **Runs only on:** Push to `main`/`master` (not PRs) AND all previous jobs passed
- Builds and pushes Docker images to container registry (Docker Hub or GHCR):
  - `careerai-web` (multi-stage, production optimized)
  - `careerai-api` (production target, non-root user)
  - `careerai-worker` (Celery, production target)
- Tags: `main`, git SHA, semantic version (if applicable)
- Uses GitHub Actions cache for layer reuse across builds

**Requirement:** Configure `DOCKER_USERNAME`, `DOCKER_PASSWORD`, and `DOCKER_REGISTRY` in repository secrets

---

### 2. Deploy Workflow (`.github/workflows/deploy.yml`)

**Triggers:**
- Auto: After CI succeeds on `main`/`master` (deploys to **staging** automatically)
- Manual: `workflow_dispatch` with environment input (deploys to **staging** or **production**)

**Jobs:**

#### `deploy-staging`
- Logs into container registry
- Pulls the commit's Docker images
- Deploys web to Vercel (staging domain)
- Deploys api/worker to Railway or ECS
- Runs health check polling (30 attempts, 10s intervals)
- Fails fast if health check times out

**Environment:** `staging` (configured in GitHub settings with auto-deploy URL)

#### `deploy-production`
- **Manual trigger only** — requires explicit approval
- Same deployment process as staging, but to production domains
- Must be triggered manually after verifying staging
- Posts deployment status comment on the PR

**Requirement:** Configure `RAILWAY_TOKEN` or AWS credentials in environment-specific secrets

---

### 3. Security & Dependencies Workflow (`.github/workflows/security.yml`)

**Triggers:** Daily at 2 AM UTC + manual dispatch

**Jobs:**

#### `dependency-check`
- Runs npm audit and pip-audit
- Checks for HIGH/CRITICAL vulnerabilities
- Fails if critical issues found

#### `trivy-scan`
- Scans filesystem for CVE vulnerabilities
- Scans Dockerfiles/configs for misconfigurations
- Uploads SARIF results

#### `secret-scan`
- Uses GitGuardian to detect exposed secrets (API keys, tokens, etc.)
- Continues on error (doesn't block merge, but alerts)

#### `license-scan`
- Checks npm and Python packages against approved licenses
- Whitelisted: MIT, Apache-2.0, ISC, BSD variants, Unlicense
- Runs daily to catch new dependencies

**Requirement:** Set `GITGUARDIAN_API_KEY` in repository secrets for secret detection

---

### 4. Compatibility Matrix Workflow (`.github/workflows/compatibility.yml`)

**Triggers:** Push/PR on files in `apps/api/`, `apps/web/`, or package files

**Jobs:**

#### `python-matrix`
- Tests against Python 3.11 and 3.12 (pinned in `engine` field)
- Runs all tests in each environment

#### `node-matrix`
- Tests against Node 20 and 22 (pinned in `engines` field)
- Runs linting, type checking, tests, and build

**Purpose:** Ensures the app works on all declared language versions; catches accidental version-specific code

---

## Local Development

### Pre-commit Hooks

Before committing, run local checks to avoid CI failures:

```bash
# Install pre-commit framework
pip install pre-commit

# Install hooks into .git
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

**Hooks included:**
- Trailing whitespace, YAML/JSON validation
- Ruff (Python linting + formatting)
- mypy (Python type checking)
- ESLint (JavaScript/TypeScript)
- Secret detection (private key patterns)
- Hadolint (Dockerfile linting)

### Running CI Locally

```bash
# Backend — full CI
cd apps/api
docker-compose up -d postgres redis
pip install -r requirements/dev.txt
ruff check .
ruff format --check .
mypy app
alembic upgrade head
pytest -v

# Frontend
npm ci
npm run lint:web
npm run typecheck:web
npm run test:web
npm run build:web
```

---

## Deployment Strategy

### Environments

| Environment | Branch | Deployment | Manual Approval | Data |
|---|---|---|---|---|
| Staging | `main` | Automatic on CI success | No | Non-production |
| Production | `main` (via manual workflow) | Manual | Yes | Real user data |

### Docker Image Promotion

1. **Build:** CI builds once on `main` push
2. **Tag:** `main`, git SHA, semantic version (e.g., `v1.2.3`)
3. **Push:** To Docker Hub or GHCR
4. **Promote to staging:** Automatic after build success
5. **Promote to production:** Manual, same image as staging (no rebuild)

### Health Checks

After deployment, the pipeline polls `/api/v1/health` until it responds or times out (300s). This ensures:
- The container is running
- The app started successfully
- External services (DB, Redis) are reachable

---

## Configuration

### GitHub Repository Secrets

| Secret | Purpose | Example |
|---|---|---|
| `DOCKER_USERNAME` | Docker Hub login | `myusername` |
| `DOCKER_PASSWORD` | Docker Hub token | (create via Docker Hub) |
| `DOCKER_REGISTRY` | Registry URL | `docker.io/myusername` |
| `RAILWAY_TOKEN` | Railway.app API token | (from Railway dashboard) |
| `GITGUARDIAN_API_KEY` | GitGuardian scanning | (from GitGuardian) |

### Environment-Specific Secrets

Create separate environments in GitHub repo settings:

**Staging:**
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY`
- `OPENAI_API_KEY` (staging budget)
- `UPSTASH_REDIS_URL`
- Any staging-specific config

**Production:**
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (prod Supabase project)
- `OPENAI_API_KEY` (prod budget — separate from staging)
- `UPSTASH_REDIS_URL` (prod instance)
- `DATABASE_URL`, `REDIS_URL`

---

## Troubleshooting

### CI Failures

**Build fails on linting:**
```bash
cd apps/api
ruff check . --fix
ruff format .
cd ../..
```

**Type check fails:**
```bash
cd apps/api
mypy app --show-error-codes
```

**Tests fail locally but pass in CI:**
- Check Python/Node versions match the workflow matrix
- Ensure services (Postgres, Redis) are running
- Check `.env` has all required values (or use CI's test values)

**Docker build fails:**
```bash
# Build locally to debug
docker build -f infrastructure/docker/Dockerfile.api -t test-api:latest .
docker build -f infrastructure/docker/Dockerfile.web -t test-web:latest .
```

### Deployment Failures

**Health check timeout:**
- Pod/container failed to start — check logs: `kubectl logs <pod>` or platform-specific logs
- Database/Redis unreachable — verify connectivity in the deployment environment
- App takes >300s to start — increase health check timeout or optimize startup

**Image not found:**
- Verify image was built and pushed: `docker images`, `docker push`
- Check registry credentials in secrets

---

## Best Practices

1. **Keep CI fast** — optimize test suite; use matrix jobs for parallel testing
2. **Fail visible** — use SARIF for security reports; comment failures on PRs
3. **No manual steps** — deployment should be one-click (or scheduled); no SSH/manual deploys
4. **Immutable images** — tag by commit SHA; don't overwrite image tags
5. **Secrets in environments** — never commit `.env` or secrets; use GitHub environments for each stage
6. **Document runbooks** — if a CI job fails, include a runbook in the workflow description

---

## Future Improvements

- **Automated rollback:** Trigger rollback workflow if production health checks fail
- **Performance benchmarks:** Track build/test/deploy times; alert if they regress
- **Slack notifications:** Post CI/deployment status to Slack channels
- **DAST:** Add dynamic security scanning against staging after deployment
- **Cost tracking:** Monitor CI minutes and Docker build costs
