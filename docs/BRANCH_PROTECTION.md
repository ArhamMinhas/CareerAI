# Branch Protection Rules

This document describes the required branch protection rules for `main` branch. These must be configured manually in GitHub UI (Settings → Branches → Branch protection rules) or via GitHub CLI.

## Main Branch Protection

### Basic Rules
- **Require pull request reviews before merging**
  - Dismissal of stale PR approvals: ✓ (enabled)
  - Require review from code owners: ✓ (enabled) — see `CODEOWNERS` file
  - Dismiss stale build status reviews: ✓ (enabled)

- **Require status checks to pass before merging**
  - Required status checks:
    - `web (lint, typecheck, test, build)`
    - `api (lint, typecheck, test)`
    - `security`
    - `build-images`
    - `python-matrix (3.11)`
    - `python-matrix (3.12)`
    - `node-matrix (20)`
    - `node-matrix (22)`

- **Require branches to be up to date before merging** ✓
  - Ensures no conflicts with `main`

- **Require code reviews before merging**
  - Number of approving reviews: **2**
  - Restriction to reviewers with write access: ✗ (off — enable for stricter control)

- **Require conversation resolution before merging** ✓
  - All review comments must be resolved

- **Require commits to be signed** ✗ (off, optional)
  - Enable for production-grade security

- **Include administrators** ✓
  - Admins are subject to the same rules

### Advanced Rules
- **Allow force pushes** ✗ (disabled)
- **Allow deletions** ✗ (disabled)
- **Lock branch** — only when cutting a release

## CODEOWNERS File

Create `.github/CODEOWNERS` to automatically request reviewers:

```
# Global owners
* @yourname

# Frontend
apps/web/ @frontend-lead @yourname
apps/web/components/ui/ @design-system-owner

# Backend
apps/api/ @backend-lead @yourname
apps/api/app/ai/ @ai-lead
apps/api/app/ml/ @data-science-lead

# Infrastructure
infrastructure/ @devops-lead
.github/workflows/ @devops-lead
docker-compose.yml @devops-lead

# Docs
docs/ @tech-lead

# Configuration
package.json @yourname
pyproject.toml @yourname
```

## GitHub CLI Setup

Apply branch protection rules programmatically (requires GitHub CLI):

```bash
# Install GitHub CLI
brew install gh  # macOS
# or download from https://github.com/cli/cli

# Authenticate
gh auth login

# Create branch protection rule
gh api repos/YOUR_ORG/careerai/branches/main/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "web (lint, typecheck, test, build)",
      "api (lint, typecheck, test)",
      "security",
      "build-images",
      "python-matrix (3.11)",
      "python-matrix (3.12)",
      "node-matrix (20)",
      "node-matrix (22)"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  },
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

## PR Checklist

Before merging, ensure:

- [ ] All required status checks pass (green checkmarks)
- [ ] At least 2 approvals from code owners
- [ ] All conversations resolved
- [ ] No conflicts with `main`
- [ ] Commits follow conventional commit format (`feat:`, `fix:`, etc.)
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Tests added for new features
- [ ] Documentation updated

## Emergency Bypass

If `main` is blocked and urgent hotfix is needed:

1. Get approval from 2+ code owners
2. Temporarily disable branch protection (Settings → Branches)
3. Merge the hotfix
4. **Immediately re-enable** branch protection
5. Post incident report in #incidents Slack channel

## Dependency Management

Dependabot-created PRs:
- Minor/patch updates auto-merge (if all checks pass)
- Major updates require manual review
- Automated via `dependabot-auto-merge` GitHub Actions job

## Review Requirements by Area

| Area | Min Reviews | Checklist |
|---|---|---|
| Web/Frontend | 1 | Layout rendering, accessibility, performance |
| API/Backend | 2 | Database migrations, backward compatibility, error handling |
| Infrastructure | 2 | Tested locally, no secrets in logs, rollback plan |
| Docs | 1 | Grammar check, links verified, format consistent |

---

**Last Updated:** Phase 6
**Next Review:** Phase 15 (hardened gates — add E2E test requirement, performance budgets)
