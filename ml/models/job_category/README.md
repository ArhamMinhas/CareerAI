# job_category

Classifies a posting's title/description into one of the 8 known role categories — backs `Job.predicted_category`, a filter facet on /jobs search.

**Current version:** 1.0.0
**Features:** title, description (first 1000 chars)
**Training window:** 400 real Adzuna postings with a known search_category, snapshot
**Metric:** f1_macro = 0.9755

**Baseline(s):**
- accuracy: 0.3750
- f1_macro: 0.2857

**Limitations:** Trained on 400 of 553 jobs (only those with a real search_category — the 153 stale jobs from before this backfill, per docs/ROADMAP.md Phase 8's notes, are excluded). 8-class problem; a job could genuinely match more than one query in reality (this label reflects which query Adzuna actually returned it under, not a mutually exclusive ground truth). Predictions for jobs outside the original 8 role queries are unvalidated — this model has never seen a job title that doesn't already resemble one of the 8 categories.

**Last retrained:** 2026-08-24T15:48:12.454445+00:00 (commit unknown)
