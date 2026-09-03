# ml/

Data science / ML pipeline, independent of the request/response cycle. Trained model
artifacts are loaded by `apps/api/app/ml` for inference.

```
data/raw/         immutable source datasets (job postings, skill taxonomies, salary data)
data/processed/   cleaned, deduplicated, validated data
data/features/    engineered feature sets used for training
models/           serialized model artifacts + a lightweight model registry (versioned)
notebooks/        01_data_collection ... 08_model_evaluation (exploration, not production logic)
training/         reusable Python modules that notebooks import (production training code)
```

See [docs/ML_PIPELINE.md](../docs/ML_PIPELINE.md) and [docs/ROADMAP.md](../docs/ROADMAP.md)'s
Phase 8 entry for the real evaluation results (including the two models that don't beat their
baseline yet).

## Setup

Deliberately isolated from `apps/api`'s dependency tree — a separate `requirements.txt`, no
FastAPI/Celery/asyncpg, and no Docker/Compose service (notebooks are interactive local-dev
tooling; see `requirements.txt`'s header comment for the full reasoning).

```bash
# From ml/, with a Python 3.12 venv active:
pip install -r requirements-dev.txt   # includes requirements.txt + pytest/ruff/mypy for CI

# Pulls a fresh snapshot from the real DB into data/raw/*.parquet (needs DATABASE_URL_SYNC —
# defaults to the same localhost:5432 convention apps/api's .env.example uses):
python -m training.data

# Runs one model's training end-to-end (loads the snapshot, evaluates vs. its real baseline,
# writes models/<name>/<version>/model.joblib + metadata.json + a model card):
python -m training.suitability   # or salary, job_category, skill_cluster, career_rank, skill_demand

# Or open a notebook — each is a thin, genuinely runnable wrapper around the same training
# modules (no inline production logic):
jupyter lab notebooks/
```

If a local Python 3.12 isn't available, the `api` dev container's own Python 3.12 works too —
`docker cp` this directory in, create a venv inside the container, and set
`DATABASE_URL_SYNC=postgresql://careerai:careerai@postgres:5432/careerai` (the Docker network
hostname, not `localhost`).
