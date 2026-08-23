import uuid
from datetime import date

from app.models.education import Education
from app.models.experience import Experience
from app.models.job import JobSkill
from app.services.job_matching import (
    WEIGHTS,
    _cosine_similarity,
    _education_subscore,
    _experience_subscore,
    _location_subscore,
    _preference_subscore,
    _semantic_similarity_subscore,
    _skill_overlap_subscore,
    _years_of_experience,
)


def _job_skill(*, weight: int, is_required: bool, skill_name: str) -> JobSkill:
    job_skill = JobSkill(
        job_id=uuid.uuid4(), skill_id=uuid.uuid4(), weight=weight, is_required=is_required
    )
    job_skill.skill = type("Skill", (), {"name": skill_name})()
    return job_skill


def _experience(*, start: date | None, end: date | None) -> Experience:
    return Experience(
        profile_id=uuid.uuid4(),
        company="Acme",
        title="Engineer",
        start_date=start,
        end_date=end,
    )


class _FakeProfile:
    def __init__(self, location: str | None) -> None:
        self.location = location


class _FakeCompany:
    def __init__(self, industry: str | None) -> None:
        self.industry = industry


class _FakeJob:
    def __init__(
        self, *, title: str = "Software Engineer", location: str | None = None, remote: bool = False
    ) -> None:
        self.title = title
        self.location = location
        self.remote = remote
        self.company = _FakeCompany(industry=None)


class _FakeCareerGoal:
    def __init__(self, target_role: str, target_industry: str | None = None) -> None:
        self.target_role = target_role
        self.target_industry = target_industry


def test_weights_sum_to_one() -> None:
    assert round(sum(WEIGHTS.values()), 6) == 1.0


def test_cosine_similarity_identical_vectors_is_one() -> None:
    assert round(_cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 6) == 1.0


def test_cosine_similarity_orthogonal_vectors_is_zero() -> None:
    assert round(_cosine_similarity([1.0, 0.0], [0.0, 1.0]), 6) == 0.0


def test_cosine_similarity_zero_vector_does_not_divide_by_zero() -> None:
    assert _cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_semantic_similarity_neutral_without_either_embedding() -> None:
    sub_score = _semantic_similarity_subscore(None, [0.1, 0.2])
    assert sub_score.score == 50.0
    assert sub_score.explanation


def test_semantic_similarity_scores_perfect_match_as_100() -> None:
    vector = [1.0, 0.5, 0.25]
    sub_score = _semantic_similarity_subscore(vector, vector)
    assert sub_score.score == 100.0


def test_skill_overlap_full_credit_when_no_required_skills() -> None:
    sub_score = _skill_overlap_subscore(set(), [])
    assert sub_score.score == 100.0


def test_skill_overlap_scores_partial_match() -> None:
    matched_skill = _job_skill(weight=10, is_required=True, skill_name="Python")
    missing_skill = _job_skill(weight=10, is_required=True, skill_name="Rust")
    user_skill_ids = {matched_skill.skill_id}

    sub_score = _skill_overlap_subscore(user_skill_ids, [matched_skill, missing_skill])

    assert sub_score.score == 50.0
    assert "Rust" in sub_score.explanation


def test_skill_overlap_weights_required_skills_more_heavily() -> None:
    required_missing = _job_skill(weight=10, is_required=True, skill_name="Python")
    optional_matched = _job_skill(weight=10, is_required=False, skill_name="Docker")
    user_skill_ids = {optional_matched.skill_id}

    sub_score = _skill_overlap_subscore(user_skill_ids, [required_missing, optional_matched])

    # required_missing carries weight*2=20, optional_matched carries weight*1=10 -> 10/30
    assert round(sub_score.score, 2) == round(100 * 10 / 30, 2)


def test_years_of_experience_sums_across_roles() -> None:
    experiences = [
        _experience(start=date(2020, 1, 1), end=date(2021, 1, 1)),
        _experience(start=date(2021, 1, 1), end=None),
    ]
    years = _years_of_experience(experiences)
    assert years > 1.0


def test_years_of_experience_skips_entries_without_start_date() -> None:
    experience = _experience(start=None, end=None)
    assert _years_of_experience([experience]) == 0.0


def test_experience_subscore_neutral_without_seniority_level() -> None:
    sub_score = _experience_subscore(5.0, None)
    assert sub_score.score == 70.0


def test_experience_subscore_full_credit_within_range() -> None:
    sub_score = _experience_subscore(6.0, "Senior")
    assert sub_score.score == 100.0


def test_experience_subscore_penalizes_underqualified() -> None:
    sub_score = _experience_subscore(0.0, "Senior")
    assert sub_score.score < 100.0


def test_experience_subscore_floors_overqualified_penalty() -> None:
    sub_score = _experience_subscore(50.0, "Entry")
    assert sub_score.score >= 60.0


def test_education_subscore_rewards_presence_not_absence() -> None:
    with_education = _education_subscore(
        [Education(profile_id=uuid.uuid4(), institution="MIT")]
    )
    without_education = _education_subscore([])

    assert with_education.score == 100.0
    assert without_education.score == 50.0


def test_preference_subscore_neutral_without_active_goal() -> None:
    sub_score = _preference_subscore(None, _FakeJob())
    assert sub_score.score == 60.0


def test_preference_subscore_rewards_matching_role() -> None:
    goal = _FakeCareerGoal(target_role="Backend Engineer")
    job = _FakeJob(title="Backend Engineer")
    sub_score = _preference_subscore(goal, job)
    # Role matches exactly (100) but there's no industry data on either side to compare, so
    # that half of the average falls back to the neutral 70 -> (100 + 70) / 2.
    assert sub_score.score == 85.0


def test_location_subscore_remote_always_matches() -> None:
    sub_score = _location_subscore(_FakeProfile("Austin, TX"), _FakeJob(remote=True))
    assert sub_score.score == 100.0


def test_location_subscore_neutral_without_data() -> None:
    sub_score = _location_subscore(None, _FakeJob(location=None))
    assert sub_score.score == 50.0


def test_location_subscore_penalizes_mismatch() -> None:
    sub_score = _location_subscore(_FakeProfile("Austin, TX"), _FakeJob(location="New York, NY"))
    assert sub_score.score == 30.0
