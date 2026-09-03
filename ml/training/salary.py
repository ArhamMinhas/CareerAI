"""Model 4 — salary prediction (docs/ML_PIPELINE.md §3, docs/ROADMAP.md Phase 8).

Regresses the midpoint of `jobs.salary_min`/`salary_max` on real posting features. Baseline —
per §3's table — is "median salary by (title, region) lookup": here, median salary by
`search_category` (the normalized 8-value label; see `app/scripts/aggregate_market_data.py`'s
docstring for why raw titles are too sparse to group by at this data volume), computed directly
from the training fold rather than the live `salary_data` table (that table is the *serving*
baseline for `/careers/[slug]`, not the evaluation baseline — using the same held-out split for
both the baseline and the model keeps the comparison honest).

Evaluated with MAE, RMSE, and residuals by seniority band (§3: "a model that's accurate on
average but bad for junior roles specifically is not acceptable") — not just an aggregate score.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from training.data import fetch_job_skills, fetch_jobs
from training.registry import save_model

MODEL_NAME = "salary_prediction"
VERSION = "1.0.0"
_SENIORITY_BUCKETS = ["intern", "entry", "junior", "mid", "senior", "staff", "lead", "principal"]


def _seniority_bucket(level: str | None) -> str:
    if not level:
        return "unspecified"
    lower = level.lower()
    return next((b for b in _SENIORITY_BUCKETS if b in lower), "unspecified")


def _build_features() -> pd.DataFrame:
    jobs = fetch_jobs()
    jobs = jobs[jobs["salary_min"].notna() & jobs["salary_max"].notna() & jobs["search_category"].notna()]
    jobs = jobs.copy()
    jobs["salary_midpoint"] = (jobs["salary_min"] + jobs["salary_max"]) / 2
    jobs["seniority_bucket"] = jobs["seniority_level"].apply(_seniority_bucket)
    jobs["remote"] = jobs["remote"].astype(int)

    job_skills = fetch_job_skills()
    skill_counts = job_skills.groupby("job_id").size().rename("required_skill_count")
    jobs = jobs.merge(skill_counts, left_on="id", right_index=True, how="left")
    jobs["required_skill_count"] = jobs["required_skill_count"].fillna(0)
    return jobs


def train() -> None:
    df = _build_features()
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    cat_cols = ["search_category", "seniority_bucket"]
    x_train_cat = encoder.fit_transform(train_df[cat_cols])
    x_test_cat = encoder.transform(test_df[cat_cols])
    num_cols = ["remote", "required_skill_count"]
    x_train = np.hstack([x_train_cat, train_df[num_cols].to_numpy()])
    x_test = np.hstack([x_test_cat, test_df[num_cols].to_numpy()])
    y_train, y_test = train_df["salary_midpoint"], test_df["salary_midpoint"]

    baseline_medians = train_df.groupby("search_category")["salary_midpoint"].median()
    overall_median = train_df["salary_midpoint"].median()
    baseline_pred = test_df["search_category"].map(baseline_medians).fillna(overall_median)
    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    baseline_rmse = mean_squared_error(y_test, baseline_pred) ** 0.5

    model = XGBRegressor(n_estimators=150, max_depth=4, learning_rate=0.1, random_state=42)
    model.fit(x_train, y_train)
    model_pred = model.predict(x_test)
    model_mae = mean_absolute_error(y_test, model_pred)
    model_rmse = mean_squared_error(y_test, model_pred) ** 0.5

    residuals_by_band: dict[str, float] = {}
    for band in test_df["seniority_bucket"].unique():
        mask = test_df["seniority_bucket"] == band
        if mask.sum() > 0:
            residuals_by_band[band] = mean_absolute_error(y_test[mask], model_pred[mask])

    print(f"baseline (median by category) MAE={baseline_mae:.0f} RMSE={baseline_rmse:.0f}")
    print(f"XGBoost MAE={model_mae:.0f} RMSE={model_rmse:.0f}")
    print(f"residual MAE by seniority band: {residuals_by_band}")

    limitations = (
        f"Trained on {len(df)} real postings across {df['search_category'].nunique()} "
        "categories; salary is the midpoint of the posted min/max range, not a real point "
        "observation. `seniority_level` is unpopulated for most postings (Adzuna doesn't supply "
        "a clean field for it), so most rows fall into the 'unspecified' seniority bucket — "
        f"per-band residuals: {residuals_by_band}. No `region` feature (all postings are "
        "currently US-only)."
    )
    save_model(
        name=MODEL_NAME,
        version=VERSION,
        model={"encoder": encoder, "model": model, "cat_cols": cat_cols, "num_cols": num_cols},
        features=[*cat_cols, *num_cols],
        training_window=f"{len(df)} real Adzuna postings, snapshot",
        baseline={"mae": baseline_mae, "rmse": baseline_rmse},
        metric="mae",
        score=model_mae,
        limitations=limitations,
        card_summary=(
            "Predicts salary midpoint from role category, seniority band, remote flag, and "
            "required-skill count. Backs `/careers/[slug]`'s predicted_salary_range field."
        ),
    )


if __name__ == "__main__":
    train()
