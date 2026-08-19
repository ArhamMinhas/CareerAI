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

See [docs/ML_PIPELINE.md](../docs/ML_PIPELINE.md). Built starting Phase 8.
