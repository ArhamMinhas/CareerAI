"""One-off generator for ml/notebooks/*.ipynb — not part of the training pipeline itself, just a
convenience for producing valid notebook JSON without hand-writing it eight times. Each notebook
is a thin, genuinely runnable wrapper around the real logic in ml/training/*.py — no inline
production logic (spec §24): every notebook's code cells only call functions already defined and
tested in ml/training/, never redefine them.
"""

import json
import uuid
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).resolve().parent.parent / "notebooks"


def nb(cells: list[tuple[str, str]]) -> dict:
    return {
        "cells": [
            {
                "id": uuid.uuid4().hex[:8],
                "cell_type": kind,
                "metadata": {},
                "source": source.splitlines(keepends=True),
                **({"outputs": [], "execution_count": None} if kind == "code" else {}),
            }
            for kind, source in cells
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


NOTEBOOKS: dict[str, list[tuple[str, str]]] = {
    "01_data_collection": [
        ("markdown", "# 01 — Data Collection\n\nPulls every real table this phase needs into `ml/data/raw/*.parquet` via `ml/training/data.py::snapshot_all()` — a real DB read, not a fixture."),
        ("code", "from training.data import snapshot_all\n\nsnapshot_all()"),
        ("markdown", "Re-run `snapshot_all()` any time the underlying tables change — every notebook after this one reads the parquet snapshot, not a live query, so results stay consistent within one analysis session."),
    ],
    "02_data_cleaning": [
        ("markdown", "# 02 — Data Cleaning\n\nReal data quality check on the snapshot — nulls, duplicates, and the specific gaps this phase's ROADMAP entry documents (thin `job_skills`/`seniority_level` coverage)."),
        ("code", "from training.data import load_snapshot\n\njobs = load_snapshot(\"jobs\")\njob_skills = load_snapshot(\"job_skills\")\nskills = load_snapshot(\"skills\")\n\nprint(\"jobs:\", jobs.shape)\nprint(\"jobs missing salary:\", jobs[\"salary_min\"].isna().sum())\nprint(\"jobs missing seniority_level:\", jobs[\"seniority_level\"].isna().sum(), \"/\", len(jobs))\nprint(\"jobs with a search_category:\", jobs[\"search_category\"].notna().sum(), \"/\", len(jobs))\nprint(\"job_skills rows:\", len(job_skills), \"-- distinct jobs covered:\", job_skills[\"job_id\"].nunique())\nprint(\"skills with an embedding:\", skills[\"embedding\"].notna().sum(), \"/\", len(skills))\nprint(\"duplicate job ids:\", jobs[\"id\"].duplicated().sum())"),
    ],
    "03_eda": [
        ("markdown", "# 03 — EDA\n\nReal distributions over the snapshot — job categories, salary spread, posting dates."),
        ("code", "from training.data import load_snapshot\n\njobs = load_snapshot(\"jobs\")\nprint(jobs[\"search_category\"].value_counts())"),
        ("code", "salary_mid = (jobs[\"salary_min\"] + jobs[\"salary_max\"]) / 2\nprint(salary_mid.describe())"),
        ("code", "import matplotlib.pyplot as plt\n\nfig, ax = plt.subplots()\nsalary_mid.dropna().hist(bins=30, ax=ax)\nax.set_title(\"Real posted salary midpoints\")\nax.set_xlabel(\"USD\")\nplt.show()"),
        ("code", "posted = jobs[\"posted_at\"].dropna()\nfig, ax = plt.subplots()\nposted.dt.to_period(\"W\").value_counts().sort_index().plot(kind=\"bar\", ax=ax)\nax.set_title(\"Real postings per week (posted_at)\")\nplt.show()"),
    ],
    "04_feature_engineering": [
        ("markdown", "# 04 — Feature Engineering\n\nCalls the real feature-building step models 4/5 train on, so this notebook always reflects what's actually fed into training rather than a separately-maintained copy."),
        ("code", "from training.salary import _build_features\n\nfeatures = _build_features()\nfeatures[[\"search_category\", \"seniority_bucket\", \"remote\", \"required_skill_count\", \"salary_midpoint\"]].head(10)"),
        ("code", "print(\"seniority bucket counts:\")\nprint(features[\"seniority_bucket\"].value_counts())"),
    ],
    "05_skill_analysis": [
        ("markdown", "# 05 — Skill Analysis\n\nRuns the real model 3 training (`training.skill_cluster.train`) and inspects its output — clusters, silhouette score, and agreement with the real hand-curated categories from `app/scripts/backfill_skill_categories.py`."),
        ("code", "from training.skill_cluster import train\n\ntrain()"),
        ("markdown", "See `ml/models/skill_clustering/README.md` for the saved model card (features, baseline, honest limitations at this taxonomy's current embedding coverage)."),
    ],
    "06_job_analysis": [
        ("markdown", "# 06 — Job Analysis\n\nRuns the real model 5 (`job_category`) and model 4 (`salary_prediction`) training and prints their real evaluation vs. baseline."),
        ("code", "from training.job_category import train as train_job_category\n\ntrain_job_category()"),
        ("code", "from training.salary import train as train_salary\n\ntrain_salary()"),
    ],
    "07_model_training": [
        ("markdown", "# 07 — Model Training\n\nRuns the remaining three models' real training end to end: job suitability (model 1), career recommendation (model 2), skill-demand forecasting (model 6)."),
        ("code", "from training.suitability import train as train_suitability\n\ntrain_suitability()"),
        ("code", "from training.career_rank import train as train_career_rank\n\ntrain_career_rank()"),
        ("code", "from training.skill_demand import train as train_skill_demand\n\ntrain_skill_demand()"),
    ],
    "08_model_evaluation": [
        ("markdown", "# 08 — Model Evaluation\n\nReads every model's real, already-saved `metadata.json` (docs/ML_PIPELINE.md §6) and prints a single comparison table — the same honest summary in `ml/models/README.md`, generated from the actual artifacts rather than transcribed by hand."),
        ("code", "import json\nfrom training.registry import MODELS_DIR\n\nfor model_dir in sorted(MODELS_DIR.iterdir()):\n    if not model_dir.is_dir():\n        continue\n    versions = sorted(p for p in model_dir.iterdir() if p.is_dir())\n    if not versions:\n        continue\n    metadata_path = versions[-1] / \"metadata.json\"\n    if not metadata_path.exists():\n        continue\n    metadata = json.loads(metadata_path.read_text())\n    print(f\"{metadata['name']} ({metadata['version']}): {metadata['metric']}={metadata['score']:.4f}\")\n    print(f\"  baseline: {metadata['baseline']}\")\n    print(f\"  limitations: {metadata['limitations'][:200]}...\")\n    print()"),
    ],
}


def main() -> None:
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        path = NOTEBOOKS_DIR / f"{name}.ipynb"
        path.write_text(json.dumps(nb(cells), indent=1))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
