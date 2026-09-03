"""CI coverage for ml/training/*.py's pure functions only (docs/ROADMAP.md Phase 8) —
self-contained fixtures, no real DB, matching the established "CI tests never depend on seeded
data" precedent from apps/api/tests. Real model training/notebooks don't run in CI at all; see
this repo's .github/workflows/ci.yml for the `ml` job's scope.
"""

import numpy as np
import pandas as pd
import pytest

from training.career_rank import _cosine
from training.data import parse_vector_column
from training.job_category import _keyword_baseline_predict
from training.salary import _seniority_bucket
from training.skill_demand import _linear_forecast


def test_parse_vector_column_parses_json_text() -> None:
    series = pd.Series(["[0.1,0.2,0.3]", "[1.0,2.0,3.0]"])
    result = parse_vector_column(series)
    assert np.allclose(result[0], [0.1, 0.2, 0.3])
    assert np.allclose(result[1], [1.0, 2.0, 3.0])


def test_parse_vector_column_none_for_null() -> None:
    series = pd.Series(["[0.1,0.2]", None])
    result = parse_vector_column(series)
    assert result[1] is None


def test_seniority_bucket_matches_known_levels() -> None:
    assert _seniority_bucket("Senior Backend Engineer") == "senior"
    assert _seniority_bucket("Junior Developer") == "junior"
    assert _seniority_bucket(None) == "unspecified"
    assert _seniority_bucket("Some Unrecognized Title") == "unspecified"


def test_keyword_baseline_predict_matches_category_word_in_title() -> None:
    categories = ["backend engineer", "frontend engineer", "data scientist"]
    assert _keyword_baseline_predict("Senior Backend Engineer", categories) == "backend engineer"
    assert _keyword_baseline_predict("Data Scientist II", categories) == "data scientist"


def test_keyword_baseline_predict_falls_back_to_first_category() -> None:
    categories = ["backend engineer", "frontend engineer"]
    assert _keyword_baseline_predict("Totally Unrelated Title", categories) == "backend engineer"


def test_linear_forecast_extrapolates_upward_trend() -> None:
    # 1, 2, 3, 4 -> next point should continue the trend around 5 (np.polyfit's least-squares
    # fit introduces float error, so this is a tolerance check, not exact equality).
    assert _linear_forecast([1.0, 2.0, 3.0, 4.0]) == pytest.approx(5.0)


def test_linear_forecast_flat_series_stays_flat() -> None:
    assert _linear_forecast([5.0, 5.0, 5.0]) == pytest.approx(5.0)


def test_cosine_identical_vectors_is_one() -> None:
    a = np.array([1.0, 2.0, 3.0])
    assert abs(_cosine(a, a) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors_is_zero() -> None:
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(_cosine(a, b)) < 1e-9


def test_cosine_zero_vector_does_not_divide_by_zero() -> None:
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 1.0])
    assert _cosine(a, b) == 0.0
