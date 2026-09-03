"""Model 6 — skill-demand forecasting (docs/ML_PIPELINE.md §3, docs/ROADMAP.md Phase 8).

Simple linear trend (chosen over Prophet — see ml/README.md/docs/ROADMAP.md's scope notes;
Prophet's cmdstanpy/Stan backend is fragile to install for a series this short anyway) over
`skill_demand.demand_count`, one fit per skill with enough history. Baseline — per §3's table —
is "naive last-period-value forecast" (predict next period = this period's count).

Evaluated via a real rolling backtest: for each skill with >= MIN_PERIODS weekly buckets, hold
out its most recent period, fit the trend line on everything before it, and compare both
forecasts against the actual held-out value. Only ~19 of 66 skills currently have enough
history for this — documented honestly, not silently dropped.
"""

import numpy as np
import pandas as pd

from training.data import fetch_skill_demand, fetch_skills
from training.registry import save_model

MODEL_NAME = "skill_demand_forecast"
VERSION = "1.0.0"
MIN_PERIODS = 3


def _linear_forecast(counts: list[float]) -> float:
    x = np.arange(len(counts))
    slope, intercept = np.polyfit(x, counts, 1)
    return float(slope * len(counts) + intercept)


def train() -> None:
    demand = fetch_skill_demand()
    skills = fetch_skills()[["id", "name"]].rename(columns={"id": "skill_id"})
    demand = demand.merge(skills, on="skill_id")
    demand["period"] = pd.to_datetime(demand["period"])
    demand = demand.sort_values("period")

    naive_errors: list[float] = []
    trend_errors: list[float] = []
    per_skill_trend: dict[str, float] = {}
    eligible_skills = 0

    for skill_id, group in demand.groupby("skill_id"):
        counts = group["demand_count"].tolist()
        if len(counts) < MIN_PERIODS:
            continue
        eligible_skills += 1
        history, held_out = counts[:-1], counts[-1]

        naive_pred = history[-1]
        trend_pred = _linear_forecast(history)
        naive_errors.append(abs(held_out - naive_pred))
        trend_errors.append(abs(held_out - trend_pred))

        # Full-history fit (all periods, not the leave-one-out fold) is what actually backs the
        # live "next period" forecast shown on /skills/[slug] (docs/ROADMAP.md Phase 8, E.6) —
        # stored as the already-evaluated next-period value, not (slope, intercept), since
        # inference has no reason to know each skill's original period count to re-derive it.
        forecast = max(0.0, _linear_forecast(counts))
        per_skill_trend[str(skill_id)] = forecast

    naive_mae = float(np.mean(naive_errors)) if naive_errors else float("nan")
    trend_mae = float(np.mean(trend_errors)) if trend_errors else float("nan")
    print(f"eligible skills (>= {MIN_PERIODS} periods): {eligible_skills}")
    print(f"baseline (naive last-period-value) MAE: {naive_mae:.4f}")
    print(f"linear trend MAE: {trend_mae:.4f}")

    limitations = (
        f"Only {eligible_skills} of {len(demand['skill_id'].unique())} skills with any demand "
        f"data have >= {MIN_PERIODS} weekly periods to backtest against — most of the taxonomy "
        "has too short a real history yet for this model to say anything about. Weekly buckets "
        "span a few months of real Adzuna posting dates (not months of live production traffic), "
        "so this evaluates a real but early-stage trend, not a mature forecast."
    )
    save_model(
        name=MODEL_NAME,
        version=VERSION,
        model={"per_skill_trend": per_skill_trend},
        features=["skill_demand.demand_count (weekly time series)"],
        training_window=f"{eligible_skills} skills with >= {MIN_PERIODS} weekly periods",
        baseline={"naive_last_period_mae": naive_mae},
        metric="mae",
        score=trend_mae,
        limitations=limitations,
        card_summary=(
            "Forecasts next-period demand count per skill via a simple linear trend — backs "
            "the demand-trend chart on /skills/[slug]."
        ),
    )


if __name__ == "__main__":
    train()
