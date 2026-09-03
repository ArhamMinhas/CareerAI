# salary_prediction

Predicts salary midpoint from role category, seniority band, remote flag, and required-skill count. Backs `/careers/[slug]`'s predicted_salary_range field.

**Current version:** 1.0.0
**Features:** search_category, seniority_bucket, remote, required_skill_count
**Training window:** 400 real Adzuna postings, snapshot
**Metric:** mae = 30230.8247

**Baseline(s):**
- mae: 31667.4229
- rmse: 41988.2611

**Limitations:** Trained on 400 real postings across 8 categories; salary is the midpoint of the posted min/max range, not a real point observation. `seniority_level` is unpopulated for most postings (Adzuna doesn't supply a clean field for it), so most rows fall into the 'unspecified' seniority bucket — per-band residuals: {'unspecified': 30230.824660156253}. No `region` feature (all postings are currently US-only).

**Last retrained:** 2026-08-24T15:46:47.440802+00:00 (commit unknown)
