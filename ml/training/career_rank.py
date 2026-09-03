"""Model 2 — career recommendation / ranking (docs/ML_PIPELINE.md §3, docs/ROADMAP.md Phase 8).

Real-data reality check, stated up front rather than discovered by a reader later: of the users
with any `skill_gaps` history, only **one** has ever computed gaps against all 8 career paths —
every other user in the data only ever queried a single target role (real usage so far, not a
data bug). A ranking model needs a candidate ranked against *multiple* items to mean anything, so
this model trains and evaluates on that one real user's 8 real (career_path, coverage%) pairs via
leave-one-path-out — genuinely real data, but N=1 candidate. This is explicitly a
proof-of-methodology exercise, not a validated recommender; retrain once more users have
skill-gap history across multiple career paths.

Baseline — per §3's table — is "cosine similarity on embeddings alone" (rank career paths by
resume-to-career-path-embedding cosine similarity, no model). Relevance label = skill-gap
coverage percentage (adequate+strong skills / total required) per (user, career_path) — already-
real, already-computed `skill_gaps` data, not fabricated.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression

from training.data import (
    fetch_career_path_skills,
    fetch_career_paths,
    fetch_skill_gaps,
    fetch_users_with_resume_embeddings,
)
from training.registry import save_model

MODEL_NAME = "career_recommendation"
VERSION = "1.0.0"
# `gap_level` comes back from `pd.read_sql` as the raw Postgres enum value — uppercase
# ("ADEQUATE", "STRONG"), not the lowercase `GapLevel` enum member names.
_COVERED_LEVELS = {"ADEQUATE", "STRONG"}


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def _build_dataset() -> pd.DataFrame:
    gaps = fetch_skill_gaps()
    career_paths = fetch_career_paths()
    path_skills = fetch_career_path_skills()
    users = fetch_users_with_resume_embeddings()

    coverage = (
        gaps.assign(covered=gaps["gap_level"].isin(_COVERED_LEVELS))
        .groupby(["user_id", "target_role"])["covered"]
        .mean()
        .rename("coverage")
        .reset_index()
    )
    # Only keep users with coverage rows for every published career path — see module docstring.
    full_coverage_users = (
        coverage.groupby("user_id")["target_role"].nunique()[lambda s: s == len(career_paths)].index
    )
    coverage = coverage[coverage["user_id"].isin(full_coverage_users)]

    coverage = coverage.merge(career_paths, left_on="target_role", right_on="slug")
    coverage = coverage.merge(users, on="user_id")
    required_counts = path_skills.groupby("career_path_id").size().rename("required_skill_count")
    coverage = coverage.merge(required_counts, left_on="id", right_index=True)

    coverage["cosine_similarity"] = coverage.apply(
        lambda row: _cosine(row["embedding_x"], row["embedding_y"]), axis=1
    )
    return coverage


def train() -> None:
    df = _build_dataset()
    n_users = df["user_id"].nunique()
    print(f"users with full career-path coverage: {n_users}, rows: {len(df)}")

    baseline_corrs: list[float] = []
    model_corrs: list[float] = []
    for _user_id, group in df.groupby("user_id"):
        group = group.reset_index(drop=True)
        baseline_rho, _ = spearmanr(group["cosine_similarity"], group["coverage"])
        baseline_corrs.append(baseline_rho if not np.isnan(baseline_rho) else 0.0)

        # Leave-one-path-out: fit on n-1 paths, predict the held-out path's relative rank via
        # the fitted model, then correlate ALL n predictions (n-1 in-sample + 1 held-out) against
        # true coverage — the closest a real held-out evaluation gets with only 8 items total.
        preds = np.zeros(len(group))
        for i in range(len(group)):
            train_rows = group.drop(index=i)
            reg = LinearRegression()
            reg.fit(
                train_rows[["cosine_similarity", "required_skill_count"]], train_rows["coverage"]
            )
            preds[i] = reg.predict(group.loc[[i], ["cosine_similarity", "required_skill_count"]])[0]
        model_rho, _ = spearmanr(preds, group["coverage"])
        model_corrs.append(model_rho if not np.isnan(model_rho) else 0.0)

    baseline_score = float(np.mean(baseline_corrs))
    model_score = float(np.mean(model_corrs))
    print(f"baseline (cosine similarity alone) mean Spearman rho: {baseline_score:.4f}")
    print(f"model (cosine similarity + required-skill-count) mean Spearman rho: {model_score:.4f}")

    final_model = LinearRegression()
    final_model.fit(df[["cosine_similarity", "required_skill_count"]], df["coverage"])

    limitations = (
        f"Only {n_users} real user(s) have skill-gap coverage computed against every published "
        "career path — a ranking model fundamentally needs a candidate ranked against multiple "
        "items, so this is a leave-one-path-out evaluation on that single real candidate's 8 "
        "real (career_path, coverage) pairs, not a validated multi-user recommender. Spearman "
        f"correlation, model vs. baseline: {model_score:.4f} vs {baseline_score:.4f}. Retrain "
        "once more users have queried skill gaps against multiple career paths."
    )
    save_model(
        name=MODEL_NAME,
        version=VERSION,
        model=final_model,
        features=["cosine_similarity", "required_skill_count"],
        training_window=f"{n_users} user(s) x {df['target_role'].nunique()} career paths, snapshot",
        baseline={"spearman_rho_cosine_only": baseline_score},
        metric="spearman_rho",
        score=model_score,
        limitations=limitations,
        card_summary=(
            "Ranks career paths for a candidate — backs GET /api/v1/career-recommendations and "
            "a dashboard-home card, alongside cosine-similarity ranking as the fallback baseline."
        ),
    )


if __name__ == "__main__":
    train()
