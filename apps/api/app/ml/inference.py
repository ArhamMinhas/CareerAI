"""One `predict_*`/`forecast_*` function per trained model (docs/ML_PIPELINE.md §3, docs/
ROADMAP.md Phase 8) — all cheap/fast (small feature vectors, no LLM calls), so inference runs
synchronously in the request, no Celery task (ML_PIPELINE.md §6: "synchronous for fast models").
Every function returns `None` when the underlying artifact isn't loaded (see
`app/ml/registry.py`) — callers render a graceful "unavailable" state, never a 500.
"""

import json

import numpy as np

from app.core.config import settings
from app.ml import registry
from app.ml.features import seniority_bucket

_JOB_SUITABILITY_FEATURES = [
    "semantic_similarity",
    "skill_overlap",
    "experience_match",
    "education_match",
    "preference_match",
    "location_match",
]


def predict_job_suitability(scores: dict[str, float]) -> float | None:
    """`scores` is the same 6 sub-scores `job_matching.py::compute_job_fit`'s breakdown already
    computes. Supplementary signal alongside the deterministic `job_match_score`, not a
    replacement — see ml/models/job_suitability/README.md for why (the model doesn't clear its
    real baseline by a meaningful margin on the data it was trained on)."""
    model = registry.load(name="job_suitability", version=settings.model_version_job_suitability)
    if model is None:
        return None
    row = [[scores[f] for f in _JOB_SUITABILITY_FEATURES]]
    return float(model.predict_proba(row)[0][1])


def predict_career_fit_score(
    *, cosine_similarity: float, required_skill_count: int
) -> float | None:
    """Observability signal only — `GET /api/v1/career-recommendations` ranks by
    `cosine_similarity` (the baseline) since it beat this model on the one real evaluation
    available (ml/models/career_recommendation/README.md). Exposed here so the model's own
    prediction can be logged/compared against real usage, not to drive the live ranking."""
    model = registry.load(
        name="career_recommendation", version=settings.model_version_career_recommendation
    )
    if model is None:
        return None
    return float(model.predict([[cosine_similarity, required_skill_count]])[0])


def skill_cluster_family(skill_id: str) -> str | None:
    """The human-nameable "skill family" badge shown on /skills/[slug] — a real curated
    category name (the cluster's dominant `Skill.category`), not a synthetic cluster index."""
    artifact = registry.load(
        name="skill_clustering", version=settings.model_version_skill_clustering
    )
    if artifact is None or skill_id not in artifact["skill_ids"]:
        return None
    idx = artifact["skill_ids"].index(skill_id)
    cluster_id = int(artifact["kmeans"].labels_[idx])
    return artifact["cluster_family_names"].get(cluster_id)


def predict_salary_range(
    *, search_category: str, seniority_level: str | None, remote: bool, required_skill_count: int
) -> tuple[float, float, float] | None:
    """Returns (p25, p50, p75). p50 is the trained model's point prediction; p25/p75 are a
    symmetric spread around it using the model's own held-out MAE (ml/models/salary_prediction/
    metadata.json) — an approximation, not a re-derived real percentile distribution, since the
    underlying model predicts a single midpoint, not a range. Backs `/careers/[slug]`."""
    artifact = registry.load(
        name="salary_prediction", version=settings.model_version_salary_prediction
    )
    if artifact is None:
        return None
    encoder, model = artifact["encoder"], artifact["model"]
    cat_row = encoder.transform([[search_category, seniority_bucket(seniority_level)]])
    num_row = np.array([[int(remote), required_skill_count]])
    row = np.hstack([cat_row, num_row])
    p50 = float(model.predict(row)[0])
    mae = _model_mae()
    if mae is None:
        return p50, p50, p50
    return max(0.0, p50 - mae), p50, p50 + mae


def _model_mae() -> float | None:
    path = (
        registry.MODELS_DIR
        / "salary_prediction"
        / settings.model_version_salary_prediction
        / "metadata.json"
    )
    if not path.exists():
        return None
    return float(json.loads(path.read_text())["score"])


def predict_job_category(*, title: str, description: str) -> str | None:
    """Backs `Job.predicted_category`, computed at ingestion/backfill time — the label space is
    the same 8 real `search_category` values (app/models/job.py's docstring)."""
    artifact = registry.load(name="job_category", version=settings.model_version_job_category)
    if artifact is None:
        return None
    text = f"{title} {description[:1000]}"
    row = artifact["vectorizer"].transform([text])
    return str(artifact["model"].predict(row)[0])


def forecast_skill_demand(skill_id: str) -> float | None:
    """Next-period demand-count forecast for one skill — `None` for a skill with too little
    history to have been included in training (ml/training/skill_demand.py's MIN_PERIODS)."""
    artifact = registry.load(
        name="skill_demand_forecast", version=settings.model_version_skill_demand_forecast
    )
    if artifact is None:
        return None
    return artifact["per_skill_trend"].get(skill_id)
