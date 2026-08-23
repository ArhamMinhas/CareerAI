# CI/CD Pipeline Setup — Summary

## Overview

A comprehensive, production-ready CI/CD pipeline has been created for CareerAI. It follows industry best practices: fail-fast on code quality, automatic security scanning, deterministic Docker builds, and safe deployment gates.

---

## Files Created/Updated

### GitHub Actions Workflows

1. **`.github/workflows/ci.yml`** (Enhanced)
   - **Stages:** Lint → Type Check → Test → Security Scan → Build Docker Images
   - **Jobs:**
     - `web` — Next.js: ESLint, tsc, Vitest, build
     - `api` — FastAPI: Ruff, mypy, pytest with live DB/Redis
     - `security` — Trivy vulnerability scan, npm audit
     - `build-images` — Multi-stage Docker builds (only on push to main, after all tests pass)
   - **Key Features:**
     - Concurrent job execution for speed
     - Docker layer caching (GitHub Actions cache)
     - Security uploads to GitHub Security tab (SARIF format)

2. **`.github/workflows/deploy.yml`** (New)
   - **Auto-staging:** Triggers on CI success → deploys to staging
   - **Manual production:** `workflow_dispatch` required for production
   - **Health checks:** Polls `/api/v1/health` with retry logic
   - **Deployment targets:**
     - Web → Vercel (via API)
     - API/Worker → Railway or AWS ECS (via tokens)

3. **`.github/workflows/security.yml`** (New)
   - **Schedule:** Daily at 2 AM UTC + manual dispatch
   - **Scans:**
     - npm audit (dependency vulnerabilities)
     - pip-audit (Python dependency vulnerabilities)
     - Trivy filesystem + config scans (CVEs, misconfigurations)
     - GitGuardian (secret detection)
     - License compliance check

4. **`.github/workflows/compatibility.yml`** (New)
   - **Matrix testing:** Python 3.11 & 3.12, Node 20 & 22
   - **Ensures:** Code works on all declared language versions
   - **Runs on:** Code changes in apps or package.json

5. **`.github/workflows/pr-validation.yml`** (New)
   - **PR checks:**
     - Title format validation (`feat:`, `fix:`, etc.)
     - Test coverage detection
     - Auto-labeling by area (web, api, infra, docs)
     - File size warnings
     - Breaking change detection
   - **Dependabot:** Auto-merge minor/patch updates

6. **`.github/workflows/release.yml`** (New)
   - **Manual release:** Version input validation
   - **Create GitHub Release:** Auto-generate changelog from commits
   - **Tag & push:** Docker images tagged with version + `latest`
   - **Slack notification:** Posts release status

### Configuration Files

7. **`.pre-commit-config.yaml`** (New)
   - **Local checks before commit:**
     - Trailing whitespace, YAML/JSON validation
     - Ruff (Python linting + formatting)
     - mypy (Python type checking)
     - ESLint (JavaScript/TypeScript)
     - Secret detection (private key patterns)
     - Hadolint (Dockerfile linting)
   - **Setup:** `pip install pre-commit && pre-commit install`

8. **`.github/CODEOWNERS`** (New)
   - **Auto-assign reviewers** by file path
   - **Examples:**
     - `apps/web/` → frontend owners
     - `apps/api/app/ai/` → AI owner
     - `infrastructure/` → DevOps owner
   - **Integration:** GitHub automatically requests these users on PRs

### Documentation

9. **`docs/CI_CD.md`** (New)
   - **Comprehensive guide:**
     - Workflow overview and triggers
     - Local development setup
     - Deployment strategy (staging → production)
     - Troubleshooting runbook
     - Configuration secrets
   - **Best practices** section

10. **`docs/BRANCH_PROTECTION.md`** (New)
    - **Branch protection rules** for `main`
    - **PR checklist** before merge
    - **CODEOWNERS setup**
    - **GitHub CLI** commands to apply rules
    - **Dependency management** (Dependabot)

11. **`Makefile`** (New)
    - **Common tasks:**
      - `make install` — Install dependencies
      - `make lint` / `make format` — Code quality
      - `make typecheck` / `make test` — Validation
      - `make build` — Build artifacts
      - `make docker-build` / `make docker-push` — Images
      - `make dev` — Local docker-compose
      - `make deploy-staging` / `make deploy-prod` — Deployments
    - **Usage:** `make help` for all targets

---

## Pipeline Flow

```
Developer Push/PR
       ↓
   [Git Hook]
     Lint, Format, Typecheck locally (pre-commit)
       ↓
  [GitHub Actions: CI]
     ├─ web: ESLint → tsc → Vitest
     ├─ api: Ruff → mypy → pytest
     ├─ security: Trivy, npm audit, GitGuardian
     └─ build-images: Docker build (main only)
       ↓
   [Status Check Gate]
     All checks pass? Yes → Ready to merge
                    No  → Block merge
       ↓
   [Merge to main]
       ↓
   [GitHub Actions: Deploy]
     └─ deploy-staging: Auto-triggers
        └─ Health check → Success/Failure
       ↓
   [Manual Approval]
     Production deployment via workflow_dispatch
       ↓
   [GitHub Actions: Release]
     Tag images, create GitHub Release, notify Slack
```

---

## Required Secrets

### Repository Secrets
```
DOCKER_USERNAME        # Docker Hub username
DOCKER_PASSWORD        # Docker Hub access token
DOCKER_REGISTRY        # docker.io/{username}
GITGUARDIAN_API_KEY    # GitGuardian API key (optional)
SLACK_WEBHOOK_URL      # Slack incoming webhook (optional)
```

### Environment Secrets

**Staging:**
```
RAILWAY_TOKEN          # Railway.app token (or AWS credentials)
SUPABASE_URL           # Supabase staging project URL
SUPABASE_SECRET_KEY    # Staging secret key
OPENAI_API_KEY         # Staging budget
DATABASE_URL           # Staging database
REDIS_URL              # Staging cache
```

**Production:**
```
RAILWAY_TOKEN          # Railway.app token (or AWS credentials)
SUPABASE_URL           # Supabase production project URL
SUPABASE_SECRET_KEY    # Production secret key
OPENAI_API_KEY         # Production budget (separate from staging)
DATABASE_URL           # Production database
REDIS_URL              # Production cache
```

---

## Quick Start

### 1. Install Pre-commit Hooks
```bash
make pre-commit-setup
```

### 2. Run CI Locally Before Pushing
```bash
make ci-local
```

### 3. Configure GitHub Branch Protection
See `docs/BRANCH_PROTECTION.md` for manual UI steps or run:
```bash
# (Requires GitHub CLI)
gh api repos/YOUR_ORG/careerai/branches/main/protection \
  --input - < branch-protection-config.json
```

### 4. Set Repository Secrets
In GitHub UI: Settings → Secrets and variables → Actions
- Add `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `DOCKER_REGISTRY`
- Add `GITGUARDIAN_API_KEY` (optional)
- Add `SLACK_WEBHOOK_URL` (optional)

### 5. Set Environment Secrets
In GitHub UI: Settings → Environments
- Create `staging` environment with staging credentials
- Create `production` environment with production credentials
- Enable "Required reviewers" for production (at least 2)

### 6. Push and Merge
- Open a PR — CI runs automatically
- 2 code owners must approve (via `.github/CODEOWNERS`)
- All status checks must pass
- Merge!

### 7. Deploy
- **Staging:** Auto-deploys after merge to main
- **Production:** Manual `workflow_dispatch` (go to Actions tab → Deploy → Run workflow)

---

## Key Features

✅ **Concurrent execution** — web and api tests run in parallel (faster feedback)
✅ **Caching** — Docker layers, npm, pip cached across builds
✅ **Security first** — Trivy, GitGuardian, secret detection on every push
✅ **Deterministic deploys** — Docker images built once, promoted through environments
✅ **Health checks** — API health verified after deployment before marking success
✅ **Local dev parity** — Pre-commit hooks catch issues before they reach CI
✅ **Multiple Python/Node versions** — Compatibility matrix ensures portability
✅ **Slack notifications** — Release status posted to team channel
✅ **Rollback ready** — Each image tagged with commit SHA + version for easy rollback

---

## Next Steps

1. **Test locally:**
   ```bash
   make lint typecheck test build
   ```

2. **Push to a branch and open PR** — watch CI run

3. **Merge to main** — staging auto-deploys

4. **Manual test staging** — https://staging.careerai.app

5. **Deploy to production** via Actions → Deploy workflow

6. **Monitor:** Check GitHub Actions logs and Slack for status

---

## Troubleshooting

**CI failing locally but passing on GitHub?**
- Check Python/Node versions match matrix
- Ensure `.env` has test values or use CI values

**Docker build timeout?**
- Increase timeout in Dockerfile steps
- Check network connectivity to registries

**Deployment stuck on health check?**
- SSH into deployed container: check logs
- Verify environment variables are set
- Check database/Redis connectivity

**Secrets not accessible?**
- Verify secrets exist in Settings → Secrets
- Check environment matches workflow expectations
- Ensure "Required reviewers" not blocking

**How to rollback?**
- Re-run deploy workflow with previous image tag
- Or: Revert the commit and push again (deploys previous version)

---

**Status:** Ready for Phase 1+ (local CI) and Phase 16+ (production deployment)
**Last Updated:** Phase 6
**Maintainer:** Your team
