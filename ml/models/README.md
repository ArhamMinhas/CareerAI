# Model Registry — Phase 8

Six trained models per [docs/ML_PIPELINE.md §3](../../docs/ML_PIPELINE.md#3-trained-ml-models).
Each subdirectory has its own model card (`README.md`) with features, baseline, metric, and
honest limitations. Artifacts (`model.joblib`) are gitignored — retrain locally via
`ml/training/<name>.py` (see [ml/README.md](../README.md)).

| Model | Metric | Model | Baseline | Beats baseline? |
|---|---|---|---|---|
| [job_suitability](./job_suitability/README.md) | ROC-AUC | 1.0000 | 1.0000 (logistic regression) | No — labels are a near-linear function of the features (honest null result, see card) |
| [career_recommendation](./career_recommendation/README.md) | Spearman ρ | 0.5238 | 0.8333 (cosine similarity) | **No** — trained on N=1 real user; live endpoint serves the baseline ranking until more data justifies the model |
| [skill_clustering](./skill_clustering/README.md) | Silhouette | 0.0929 | 0.4686 ARI vs. curated categories | Partial — clusters correlate with real categories but don't fully recover them at N=20 |
| [salary_prediction](./salary_prediction/README.md) | MAE | 30,231 | 31,667 (median by category) | Yes — modest real improvement |
| [job_category](./job_category/README.md) | F1 (macro) | 0.9755 | 0.2857 (keyword title matcher) | Yes — large real improvement |
| [skill_demand_forecast](./skill_demand_forecast/README.md) | MAE | 7.19 | 8.42 (naive last-period) | Yes — modest real improvement |

**On the two "no" rows**: per [ML_PIPELINE.md §1](../../docs/ML_PIPELINE.md#1-principle-baseline-first-model-only-if-it-earns-its-place),
a model ships because it beats its baseline, not because its accuracy looks high in isolation.
`job_suitability`'s baseline was intentionally raised past the ROADMAP-mandated one (see its
card) once the mandated one turned out to be trivially beatable by construction.
`career_recommendation` genuinely doesn't beat its baseline yet — this is reported plainly, not
hidden, and the live integration reflects it (baseline ranking, not the model, drives
`GET /api/v1/career-recommendations` for now).
