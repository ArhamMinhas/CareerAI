"""Loads trained-model artifacts (docs/ML_PIPELINE.md §6 — the artifact-layout/version-pin-
loading slice only; drift monitoring and retraining triggers stay Phase 14). Version pinned via
`Settings.model_version_*` (app/core/config.py), matching this codebase's established env-backed
config convention — the same pattern already used for `llm_model_default`/`embedding_model`.

A missing artifact (not yet trained, or a version that doesn't exist on disk) degrades
gracefully — `load()` returns `None`, never raises into a request — matching the established
Supabase-auth/embedding-cache degrade-gracefully precedent elsewhere in this codebase. Loaded
artifacts are cached in-process (module-level dict) since they're read-only and reloading a
joblib file on every request would be wasteful.
"""

import logging
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "ml_models"

_cache: dict[tuple[str, str], Any] = {}


def load(*, name: str, version: str) -> Any | None:
    key = (name, version)
    if key in _cache:
        return _cache[key]

    path = MODELS_DIR / name / version / "model.joblib"
    if not path.exists():
        logger.warning("ML model artifact not found: %s (version %s) at %s", name, version, path)
        _cache[key] = None
        return None

    try:
        model = joblib.load(path)
    except Exception:
        logger.exception("Failed to load ML model artifact: %s (version %s)", name, version)
        _cache[key] = None
        return None

    _cache[key] = model
    return model
