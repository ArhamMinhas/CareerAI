# job_suitability

Predicts P(candidate suitable for job) from the same 6 sub-scores `job_match_score` already computes — a supplementary signal alongside the deterministic score, not a replacement for it.

**Current version:** 1.0.0
**Features:** semantic_similarity, skill_overlap, experience_match, education_match, preference_match, location_match
**Training window:** 1106 (user, job) pairs, 2 users, snapshot
**Metric:** roc_auc = 1.0000

**Baseline(s):**
- skill_overlap_threshold_accuracy: 0.9459
- skill_overlap_threshold_f1: 0.9603
- logistic_regression_accuracy: 1.0000
- logistic_regression_f1: 1.0000
- logistic_regression_roc_auc: 1.0000

**Limitations:** Trained on only 2 real users' resume-vs-job features (1106 rows total, 553 jobs each) — held out by job, not by user, since a by-user split is meaningless at N=2. This is a proof-of-methodology exercise on real but scarce data, not a validated claim of generalization to a new candidate profile. XGBoost vs. logistic-regression-on-the-same-features margin (the real bar, not the skill-overlap-only baseline): +0.0000 ROC-AUC. Retrain once more users have completed, live resumes.

**Last retrained:** 2026-08-24T15:42:37.875108+00:00 (commit unknown)
