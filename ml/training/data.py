"""Pulls raw data for Phase 8 model training directly via SQL against the real Postgres
instance — deliberately NOT importing apps/api's ORM/FastAPI package (docs/ROADMAP.md Phase 8):
this keeps `ml/`'s dependency tree (pandas/scikit-learn/xgboost/jupyter) fully separate from the
API's production image, and keeps `ml/` genuinely "independent of the request/response cycle"
per ml/README.md.

Connects with the same `DATABASE_URL_SYNC` convention `apps/api` uses (see .env.example) via
plain psycopg2/SQLAlchemy core — no ORM models, just known table/column names, since the schema
is stable once a phase ships.

pgvector columns (`jobs.embedding`, `skills.embedding`) are cast to text in SQL
(`embedding::text`) and parsed here via `json.loads` + `np.array(...)`, rather than depending on
the `pgvector` Python package's psycopg2 adapter registration — one less thing to get wrong
across psycopg2 versions, and it means `ml/requirements.txt` doesn't need the `pgvector` package
at all.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _database_url() -> str:
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    return os.environ.get(
        "DATABASE_URL_SYNC", "postgresql://careerai:careerai@localhost:5432/careerai"
    )


def _engine():
    return create_engine(_database_url())


def parse_vector_column(series: pd.Series) -> pd.Series:
    """Turns a `<col>::text`-cast pgvector column (e.g. `"[0.012,-0.034,...]"` strings) into a
    Series of `np.ndarray`. `None`/NaN entries (skills/jobs with no embedding yet) stay `None` —
    `pd.isna()`, not a plain truthiness check: a NULL text column comes back from
    `pandas.read_sql` as float `nan`, which is truthy in Python (`bool(float("nan")) is True`),
    so `if v else None` would pass it straight into `json.loads` and crash on a non-string."""
    return series.apply(lambda v: None if pd.isna(v) else np.array(json.loads(v), dtype=np.float32))


def fetch_jobs() -> pd.DataFrame:
    query = """
        select id, title, description, seniority_level, employment_type, location, remote,
               salary_min, salary_max, currency, is_active, posted_at, source, external_id,
               search_category, predicted_category, embedding::text as embedding_text
        from jobs
    """
    df = pd.read_sql(query, _engine())
    df["embedding"] = parse_vector_column(df.pop("embedding_text"))
    return df


def fetch_job_skills() -> pd.DataFrame:
    return pd.read_sql(
        "select id, job_id, skill_id, is_required, weight from job_skills", _engine()
    )


def fetch_skills() -> pd.DataFrame:
    query = """
        select id, name, slug, category, synonyms, seo_summary, embedding::text as embedding_text
        from skills
    """
    df = pd.read_sql(query, _engine())
    df["embedding"] = parse_vector_column(df.pop("embedding_text"))
    return df


def fetch_career_paths() -> pd.DataFrame:
    query = """
        select id, slug, title, summary, related_job_titles, embedding::text as embedding_text
        from career_paths
    """
    df = pd.read_sql(query, _engine())
    df["embedding"] = parse_vector_column(df.pop("embedding_text"))
    return df


def fetch_career_path_skills() -> pd.DataFrame:
    return pd.read_sql(
        "select id, career_path_id, skill_id, weight, is_core from career_path_skills", _engine()
    )


def fetch_users_with_resume_embeddings() -> pd.DataFrame:
    """One row per user with an analyzed resume, joined to that resume's most recent embedding
    (`embeddings.owner_type='resume'`) — the candidate side of the suitability/career-ranking
    models' feature set. Only real users/resumes, no synthetic rows."""
    query = """
        select distinct on (r.user_id)
            r.user_id, r.id as resume_id, e.embedding::text as embedding_text
        from resumes r
        join embeddings e on e.owner_type = 'resume' and e.owner_id = r.id
        where r.deleted_at is null
        order by r.user_id, e.created_at desc
    """
    df = pd.read_sql(query, _engine())
    df["embedding"] = parse_vector_column(df.pop("embedding_text"))
    return df


def fetch_user_skills() -> pd.DataFrame:
    return pd.read_sql(
        "select id, profile_id, skill_id, proficiency, source from user_skills", _engine()
    )


def fetch_skill_demand() -> pd.DataFrame:
    return pd.read_sql(
        "select id, skill_id, demand_count, growth_rate, period from skill_demand", _engine()
    )


def fetch_skill_gaps() -> pd.DataFrame:
    return pd.read_sql(
        "select id, user_id, skill_id, target_role, gap_level, priority from skill_gaps",
        _engine(),
    )


def snapshot_all(out_dir: Path = RAW_DIR) -> None:
    """Writes every fetch_* table above to `ml/data/raw/*.parquet` — an immutable snapshot
    notebooks/training modules read from, so re-running a notebook doesn't silently pick up
    different data mid-analysis. Re-run this to refresh the snapshot."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "jobs": fetch_jobs(),
        "job_skills": fetch_job_skills(),
        "skills": fetch_skills(),
        "career_paths": fetch_career_paths(),
        "career_path_skills": fetch_career_path_skills(),
        "users_with_resume_embeddings": fetch_users_with_resume_embeddings(),
        "user_skills": fetch_user_skills(),
        "skill_gaps": fetch_skill_gaps(),
    }
    for name, df in tables.items():
        # Embedding columns are object-dtype ndarrays — parquet can't store those directly, so
        # they're serialized back to JSON text for the snapshot and re-parsed on load.
        if "embedding" in df.columns:
            df = df.copy()
            df["embedding"] = df["embedding"].apply(
                lambda v: json.dumps(v.tolist()) if v is not None else None
            )
        df.to_parquet(out_dir / f"{name}.parquet", index=False)
        print(f"wrote {len(df)} rows -> {name}.parquet")


def load_snapshot(name: str, in_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Reads one table back from the `snapshot_all()` parquet snapshot, re-parsing any
    `embedding` column from its JSON-text form into `np.ndarray`."""
    df = pd.read_parquet(in_dir / f"{name}.parquet")
    if "embedding" in df.columns:
        df["embedding"] = df["embedding"].apply(
            lambda v: np.array(json.loads(v), dtype=np.float32) if v else None
        )
    return df


if __name__ == "__main__":
    snapshot_all()
