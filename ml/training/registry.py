"""Shared model-registry writer — docs/ML_PIPELINE.md §6's artifact-layout slice only (the
drift-monitoring/retraining-trigger parts of that section stay Phase 14, per docs/ROADMAP.md
Phase 8's scope notes). Every `ml/training/<model>.py` module calls `save_model()` once, after
evaluating against its baseline(s), so all six models land in the same on-disk shape:

    ml/models/<name>/<version>/model.joblib
    ml/models/<name>/<version>/metadata.json
    ml/models/<name>/README.md   (short, human-readable model card)
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        return "unknown"


def save_model(
    *,
    name: str,
    version: str,
    model: Any,
    features: list[str],
    training_window: str,
    baseline: dict[str, float],
    metric: str,
    score: float,
    limitations: str,
    card_summary: str,
) -> Path:
    """Writes `model.joblib` + `metadata.json` under `ml/models/<name>/<version>/`, and
    (re)writes `ml/models/<name>/README.md` — the model card format docs/ML_PIPELINE.md §6
    specifies: features, training window, baseline, metric+score, limitations, retrain date."""
    out_dir = MODELS_DIR / name / version
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / "model.joblib")

    metadata = {
        "name": name,
        "version": version,
        "features": features,
        "training_window": training_window,
        "baseline": baseline,
        "metric": metric,
        "score": score,
        "limitations": limitations,
        "retrained_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    readme_dir = MODELS_DIR / name
    baseline_lines = "\n".join(f"- {k}: {v:.4f}" for k, v in baseline.items())
    readme = f"""# {name}

{card_summary}

**Current version:** {version}
**Features:** {", ".join(features)}
**Training window:** {training_window}
**Metric:** {metric} = {score:.4f}

**Baseline(s):**
{baseline_lines}

**Limitations:** {limitations}

**Last retrained:** {metadata["retrained_at"]} (commit {metadata["git_commit"]})
"""
    (readme_dir / "README.md").write_text(readme)
    return out_dir


def load_model(*, name: str, version: str) -> Any:
    path = MODELS_DIR / name / version / "model.joblib"
    return joblib.load(path)
