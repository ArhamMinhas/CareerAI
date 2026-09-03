# career_recommendation

Ranks career paths for a candidate — backs GET /api/v1/career-recommendations and a dashboard-home card, alongside cosine-similarity ranking as the fallback baseline.

**Current version:** 1.0.0
**Features:** cosine_similarity, required_skill_count
**Training window:** 1 user(s) x 8 career paths, snapshot
**Metric:** spearman_rho = 0.5238

**Baseline(s):**
- spearman_rho_cosine_only: 0.8333

**Limitations:** Only 1 real user(s) have skill-gap coverage computed against every published career path — a ranking model fundamentally needs a candidate ranked against multiple items, so this is a leave-one-path-out evaluation on that single real candidate's 8 real (career_path, coverage) pairs, not a validated multi-user recommender. Spearman correlation, model vs. baseline: 0.5238 vs 0.8333. Retrain once more users have queried skill gaps against multiple career paths.

**Last retrained:** 2026-08-24T15:55:21.373390+00:00 (commit unknown)
