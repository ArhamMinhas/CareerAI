"""Model 1 — job suitability classifier (docs/ML_PIPELINE.md §3, docs/ROADMAP.md Phase 8).

Reads the CSV `apps/api/app/scripts/export_ml_training_data.py` produces (that script reuses
`job_matching.py`'s real deterministic breakdown as the feature source — see its docstring for
why this one model's data isn't pulled via `ml/training/data.py`'s raw-SQL path).

Label = `job_match_score >= 60` (suitable). As of the training run this module was written
against, only **2 real users** have a live, analyzed resume — nowhere near enough to hold out a
user and still have anything to train on. Splitting **by job** instead (80/20, random) evaluates
generalization across postings for this fixed small set of real candidates; it does not, and
cannot yet, claim to generalize to a new candidate profile. That's stated plainly in the model
card, not hidden.

Two baselines, not one — see docs/ML_PIPELINE.md §3's table for baseline (a); baseline (b) is
the real bar this model actually needs to clear:
  (a) skill-overlap-only threshold (the ROADMAP-mandated baseline)
  (b) logistic regression on the same 6 features — since the label is a near-deterministic
      linear function of those features, a linear model can already fit the decision boundary
      almost perfectly. If XGBoost doesn't clear (b) by a real margin, that's an honest finding
      given the data scarcity, not a bug to hide.
"""

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from training.registry import save_model

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "job_suitability_training.csv"
FEATURES = [
    "semantic_similarity",
    "skill_overlap",
    "experience_match",
    "education_match",
    "preference_match",
    "location_match",
]
MODEL_NAME = "job_suitability"
VERSION = "1.0.0"


def _skill_overlap_baseline(df: pd.DataFrame, threshold: float = 60.0) -> dict[str, float]:
    predicted = (df["skill_overlap"] >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(df["suitable"], predicted),
        "f1": f1_score(df["suitable"], predicted),
    }


def train() -> None:
    df = pd.read_csv(CSV_PATH)
    train_df, test_df = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["suitable"]
    )

    x_train, y_train = train_df[FEATURES], train_df["suitable"]
    x_test, y_test = test_df[FEATURES], test_df["suitable"]

    # Baseline (a): mandated by docs/ML_PIPELINE.md §3, computed on the held-out split.
    baseline_a = _skill_overlap_baseline(test_df)

    # Baseline (b): the real bar — same 6 features, linear model.
    logistic = LogisticRegression(max_iter=1000)
    logistic.fit(x_train, y_train)
    logistic_pred = logistic.predict(x_test)
    logistic_proba = logistic.predict_proba(x_test)[:, 1]
    baseline_b = {
        "accuracy": accuracy_score(y_test, logistic_pred),
        "f1": f1_score(y_test, logistic_pred),
        "roc_auc": roc_auc_score(y_test, logistic_proba),
    }

    model = XGBClassifier(
        n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42, eval_metric="logloss"
    )
    model.fit(x_train, y_train)
    xgb_pred = model.predict(x_test)
    xgb_proba = model.predict_proba(x_test)[:, 1]
    xgb_metrics = {
        "accuracy": accuracy_score(y_test, xgb_pred),
        "f1": f1_score(y_test, xgb_pred),
        "roc_auc": roc_auc_score(y_test, xgb_proba),
    }

    print(f"baseline (a) skill-overlap-only threshold: {baseline_a}")
    print(f"baseline (b) logistic regression (6 features): {baseline_b}")
    print(f"XGBoost (6 features): {xgb_metrics}")
    margin = xgb_metrics["roc_auc"] - baseline_b["roc_auc"]
    print(f"XGBoost vs. baseline (b) ROC-AUC margin: {margin:+.4f}")

    limitations = (
        f"Trained on only 2 real users' resume-vs-job features ({len(df)} rows total, 553 jobs "
        "each) — held out by job, not by user, since a by-user split is meaningless at N=2. "
        "This is a proof-of-methodology exercise on real but scarce data, not a validated claim "
        "of generalization to a new candidate profile. XGBoost vs. logistic-regression-on-the-"
        f"same-features margin (the real bar, not the skill-overlap-only baseline): {margin:+.4f} "
        "ROC-AUC. Retrain once more users have completed, live resumes."
    )
    save_model(
        name=MODEL_NAME,
        version=VERSION,
        model=model,
        features=FEATURES,
        training_window=f"{len(df)} (user, job) pairs, {df['user_id'].nunique()} users, snapshot",
        baseline={f"skill_overlap_threshold_{k}": v for k, v in baseline_a.items()}
        | {f"logistic_regression_{k}": v for k, v in baseline_b.items()},
        metric="roc_auc",
        score=xgb_metrics["roc_auc"],
        limitations=limitations,
        card_summary=(
            "Predicts P(candidate suitable for job) from the same 6 sub-scores "
            "`job_match_score` already computes — a supplementary signal alongside the "
            "deterministic score, not a replacement for it."
        ),
    )


if __name__ == "__main__":
    train()
