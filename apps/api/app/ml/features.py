"""Small, dependency-free duplication of the pure feature-computation arithmetic from
`ml/training/*.py` — deliberate, not accidental (docs/ROADMAP.md Phase 8): `ml/` and this
package's dependency trees are kept isolated on purpose (see `ml/training/data.py`'s docstring),
so a request-path function can't import pandas-based training code. These are simple enough
(already-fetched ORM/plain data -> floats) that keeping two small copies is cheaper than the
alternative of pulling pandas into the API image just to reuse them.
"""


def seniority_bucket(level: str | None) -> str:
    """Mirrors `ml/training/salary.py::_seniority_bucket` exactly — must stay in sync with it,
    since the salary model was trained on buckets produced by that function."""
    if not level:
        return "unspecified"
    lower = level.lower()
    buckets = ["intern", "entry", "junior", "mid", "senior", "staff", "lead", "principal"]
    return next((b for b in buckets if b in lower), "unspecified")
