"""Model 5 — job category classifier (docs/ML_PIPELINE.md §3, docs/ROADMAP.md Phase 8).

Label space is explicitly the same 8 `search_category` values `app/scripts/
ingest_adzuna_jobs.py` already ingests by (see `Job`'s docstring) — a real, independent signal
(which query Adzuna matched the job against), not derived from title text, so training on it
doesn't collide with the baseline below. Predicts `Job.predicted_category`, computed once at
ingestion/backfill time, not per-request.

Baseline — per §3's table — is a keyword/regex title matcher: does any of the category's own
words (e.g. "backend" for "backend engineer") appear in the job title. Model: TF-IDF over
title+description text, multiclass logistic regression — simple, fast, appropriate for a
566-row, 8-class problem (a tree ensemble would badly overfit a TF-IDF feature space this wide
relative to this few rows).
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

from training.data import fetch_jobs
from training.registry import save_model

MODEL_NAME = "job_category"
VERSION = "1.0.0"


def _keyword_baseline_predict(title: str, categories: list[str]) -> str:
    title_lower = title.lower()
    for category in categories:
        words = [w for w in category.split() if len(w) > 3]
        if any(w in title_lower for w in words):
            return category
    return categories[0]


def train() -> None:
    jobs = fetch_jobs()
    df = jobs[jobs["search_category"].notna()].copy()
    df["text"] = df["title"].fillna("") + " " + df["description"].fillna("").str.slice(0, 1000)
    categories = sorted(df["search_category"].unique())

    train_df, test_df = train_test_split(
        df, test_size=0.2, random_state=42, stratify=df["search_category"]
    )

    baseline_pred = test_df["title"].apply(lambda t: _keyword_baseline_predict(t, categories))
    baseline_accuracy = accuracy_score(test_df["search_category"], baseline_pred)
    baseline_f1 = f1_score(test_df["search_category"], baseline_pred, average="macro")

    vectorizer = TfidfVectorizer(max_features=2000, stop_words="english", ngram_range=(1, 2))
    x_train = vectorizer.fit_transform(train_df["text"])
    x_test = vectorizer.transform(test_df["text"])

    # Recent scikit-learn versions removed `multi_class=` — LogisticRegression already handles
    # >2 classes as multinomial by default now.
    model = LogisticRegression(max_iter=1000)
    model.fit(x_train, train_df["search_category"])
    model_pred = model.predict(x_test)
    model_accuracy = accuracy_score(test_df["search_category"], model_pred)
    model_f1 = f1_score(test_df["search_category"], model_pred, average="macro")

    print(f"baseline (keyword title matcher): accuracy={baseline_accuracy:.4f} f1={baseline_f1:.4f}")
    print(f"TF-IDF + logistic regression: accuracy={model_accuracy:.4f} f1={model_f1:.4f}")

    limitations = (
        f"Trained on {len(df)} of {len(jobs)} jobs (only those with a real search_category — "
        "the 153 stale jobs from before this backfill, per docs/ROADMAP.md Phase 8's notes, are "
        "excluded). 8-class problem; a job could genuinely match more than one query in reality "
        "(this label reflects which query Adzuna actually returned it under, not a mutually "
        "exclusive ground truth). Predictions for jobs outside the original 8 role queries are "
        "unvalidated — this model has never seen a job title that doesn't already resemble one "
        "of the 8 categories."
    )
    save_model(
        name=MODEL_NAME,
        version=VERSION,
        model={"vectorizer": vectorizer, "model": model},
        features=["title", "description (first 1000 chars)"],
        training_window=f"{len(df)} real Adzuna postings with a known search_category, snapshot",
        baseline={"accuracy": baseline_accuracy, "f1_macro": baseline_f1},
        metric="f1_macro",
        score=model_f1,
        limitations=limitations,
        card_summary=(
            "Classifies a posting's title/description into one of the 8 known role categories — "
            "backs `Job.predicted_category`, a filter facet on /jobs search."
        ),
    )


if __name__ == "__main__":
    train()
