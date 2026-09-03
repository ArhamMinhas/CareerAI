"""Model 3 — skill clustering (docs/ML_PIPELINE.md §3, docs/ROADMAP.md Phase 8).

KMeans over real skill embeddings (chosen over HDBSCAN — see ml/README.md/docs/ROADMAP.md's
scope notes; ML_PIPELINE.md frames the two as interchangeable). Only 20 of 66 skills in the
taxonomy have an embedding (Phase 6 only backfilled embeddings for a curated subset) — this
model trains on those 20, honestly documented as a small-N limitation, not silently ignored.

Baseline — per §3's table — is "manually curated category labels": `Skill.category`, backfilled
for real by `app/scripts/backfill_skill_categories.py` as part of this same phase (it existed as
a column since Phase 3 but was never populated by anything until now). Evaluated via silhouette
score plus adjusted Rand index against those real category labels (a quantified version of "do
clusters make domain sense?", not just a subjective read).
"""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score

from training.data import fetch_skills
from training.registry import save_model

MODEL_NAME = "skill_clustering"
VERSION = "1.0.0"
N_CLUSTERS = 6  # roughly matches the number of distinct curated categories present


def train() -> None:
    skills = fetch_skills()
    df = skills[skills["embedding"].notna()].copy()
    embeddings = np.vstack(df["embedding"].to_numpy())

    model = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    cluster_labels = model.fit_predict(embeddings)

    silhouette = silhouette_score(embeddings, cluster_labels)
    category_labels = df["category"].fillna("Uncategorized")
    ari = adjusted_rand_score(category_labels, cluster_labels)

    print(f"silhouette score: {silhouette:.4f}")
    print(f"adjusted Rand index vs. curated categories: {ari:.4f}")
    for cluster_id in sorted(set(cluster_labels)):
        members = df.loc[cluster_labels == cluster_id, "name"].tolist()
        cats = category_labels[cluster_labels == cluster_id].value_counts().to_dict()
        print(f"cluster {cluster_id}: {members} -- categories: {cats}")

    # The "skill family" label shown on /skills/[slug] (docs/ROADMAP.md Phase 8, E.3) is the
    # cluster's most common real curated category, not a synthetic cluster index.
    cluster_family_names = {
        int(cid): category_labels[cluster_labels == cid].value_counts().idxmax()
        for cid in set(cluster_labels)
    }

    limitations = (
        f"Trained on only {len(df)} of {len(skills)} skills — the taxonomy's embedding coverage "
        "is thin (Phase 6 only backfilled a curated subset). Adjusted Rand index vs. curated "
        f"categories is {ari:.4f} (1.0 = perfect agreement, 0.0 = no better than random) — "
        "clusters partially but don't fully recover the hand-curated categories, which is "
        "expected at N=20 with 6 clusters. Retrain once embedding coverage widens."
    )
    save_model(
        name=MODEL_NAME,
        version=VERSION,
        # `apps/api/app/ml/inference.py::skill_cluster_family` takes a `str` skill_id (matching
        # every other inference function's key type here) — `df["id"]` comes back from
        # `pandas.read_sql` as `uuid.UUID` objects, which would never match a string lookup.
        model={
            "kmeans": model,
            "skill_ids": [str(sid) for sid in df["id"]],
            "cluster_family_names": cluster_family_names,
        },
        features=["skill embedding (1536-dim)"],
        training_window=f"{len(df)} skills with an embedding, snapshot",
        baseline={"adjusted_rand_index_vs_curated_categories": ari},
        metric="silhouette_score",
        score=silhouette,
        limitations=limitations,
        card_summary=(
            "Groups skills into families by embedding similarity — backs the 'skill family' "
            "badge on /skills/[slug] (a human-nameable category, not a second similarity list "
            "competing with the existing embedding-similarity 'related skills' section)."
        ),
    )


if __name__ == "__main__":
    train()
