# skill_clustering

Groups skills into families by embedding similarity — backs the 'skill family' badge on /skills/[slug] (a human-nameable category, not a second similarity list competing with the existing embedding-similarity 'related skills' section).

**Current version:** 1.0.0
**Features:** skill embedding (1536-dim)
**Training window:** 20 skills with an embedding, snapshot
**Metric:** silhouette_score = 0.0929

**Baseline(s):**
- adjusted_rand_index_vs_curated_categories: 0.4686

**Limitations:** Trained on only 20 of 66 skills — the taxonomy's embedding coverage is thin (Phase 6 only backfilled a curated subset). Adjusted Rand index vs. curated categories is 0.4686 (1.0 = perfect agreement, 0.0 = no better than random) — clusters partially but don't fully recover the hand-curated categories, which is expected at N=20 with 6 clusters. Retrain once embedding coverage widens.

**Last retrained:** 2026-08-24T17:33:23.093928+00:00 (commit unknown)
