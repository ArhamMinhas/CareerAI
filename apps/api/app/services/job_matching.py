import math
import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_goal import CareerGoal
from app.models.education import Education
from app.models.embedding import Embedding
from app.models.experience import Experience
from app.models.job import Job, JobSkill
from app.models.job_match import JobMatch
from app.models.profile import Profile
from app.models.resume import Resume, ResumeStatus
from app.models.skill import UserSkill
from app.models.user import User
from app.schemas.job_match import JobMatchBreakdown, JobMatchSubScore

CANDIDATE_POOL_SIZE = 50

# docs/ML_PIPELINE.md §2.2 — the hybrid job_match_score formula. No LLM call (docs/
# AI_ARCHITECTURE.md §1): every component is a deterministic computation over data already on
# the user's profile/resume, same "LLMs reason, code decides" precedent as the skill-gap engine
# (app/services/skill_gap.py).
WEIGHTS: dict[str, float] = {
    "semantic_similarity": 0.35,
    "skill_overlap": 0.25,
    "experience_match": 0.15,
    "education_match": 0.10,
    "preference_match": 0.10,
    "location_match": 0.05,
}

# Substring-matched against a job's free-text `seniority_level` (there's no controlled enum for
# it — postings phrase this however the listing source did), lowercased. Ordered so a more
# specific key (e.g. "senior") isn't shadowed by checking a shorter one first.
_SENIORITY_YEAR_RANGES: list[tuple[str, tuple[float, float]]] = [
    ("intern", (0, 1)),
    ("entry", (0, 2)),
    ("junior", (0, 2)),
    ("associate", (1, 3)),
    ("mid", (2, 5)),
    ("senior", (5, 9)),
    ("staff", (7, 12)),
    ("lead", (7, 12)),
    ("principal", (10, 20)),
    ("director", (10, 25)),
    ("executive", (12, 30)),
]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _semantic_similarity_subscore(
    resume_vector: list[float] | None, job_vector: list[float] | None
) -> JobMatchSubScore:
    weight = WEIGHTS["semantic_similarity"]
    if resume_vector is None or job_vector is None:
        return JobMatchSubScore(
            score=50.0,
            weight=weight,
            explanation="No resume or posting embedding available yet for semantic comparison.",
        )
    cosine = _cosine_similarity(resume_vector, job_vector)
    score = max(0.0, min(100.0, (cosine + 1) / 2 * 100))
    return JobMatchSubScore(
        score=round(score, 2),
        weight=weight,
        explanation=f"Resume-to-posting semantic similarity is {cosine:.2f} (cosine).",
    )


def _skill_overlap_subscore(
    user_skill_ids: set[uuid.UUID], job_skills: list[JobSkill]
) -> JobMatchSubScore:
    weight = WEIGHTS["skill_overlap"]
    if not job_skills:
        return JobMatchSubScore(
            score=100.0, weight=weight, explanation="This posting doesn't name any required skills."
        )

    total_weight = 0
    matched_weight = 0
    matched_names: list[str] = []
    missing_names: list[str] = []
    for job_skill in job_skills:
        skill_weight = job_skill.weight * (2 if job_skill.is_required else 1)
        total_weight += skill_weight
        if job_skill.skill_id in user_skill_ids:
            matched_weight += skill_weight
            matched_names.append(job_skill.skill.name)
        else:
            missing_names.append(job_skill.skill.name)

    score = 100.0 * matched_weight / total_weight if total_weight else 100.0
    explanation = f"Matches {len(matched_names)} of {len(job_skills)} listed skills."
    if missing_names:
        explanation += f" Missing: {', '.join(missing_names[:5])}."
    return JobMatchSubScore(score=round(score, 2), weight=weight, explanation=explanation)


def _years_of_experience(experiences: list[Experience]) -> float:
    today = date.today()
    total_days = 0
    for experience in experiences:
        if experience.start_date is None:
            continue
        end = experience.end_date or today
        total_days += max(0, (end - experience.start_date).days)
    return total_days / 365.25


def _experience_subscore(years: float, seniority_level: str | None) -> JobMatchSubScore:
    weight = WEIGHTS["experience_match"]
    if not seniority_level:
        return JobMatchSubScore(
            score=70.0,
            weight=weight,
            explanation="Posting doesn't specify a seniority level to compare experience against.",
        )

    level_lower = seniority_level.lower()
    matched_range = next((rng for key, rng in _SENIORITY_YEAR_RANGES if key in level_lower), None)
    if matched_range is None:
        return JobMatchSubScore(
            score=70.0,
            weight=weight,
            explanation=f"Unrecognized seniority level '{seniority_level}'; treated as neutral.",
        )

    low, high = matched_range
    if low <= years <= high:
        score = 100.0
    elif years < low:
        score = max(0.0, 100.0 - (low - years) * 20)
    else:
        score = max(60.0, 100.0 - (years - high) * 5)
    return JobMatchSubScore(
        score=round(score, 2),
        weight=weight,
        explanation=(
            f"{years:.1f} years of experience against a '{seniority_level}' posting "
            f"(expects roughly {low:.0f}-{high:.0f})."
        ),
    )


def _education_subscore(educations: list[Education]) -> JobMatchSubScore:
    weight = WEIGHTS["education_match"]
    if educations:
        noun = "entry" if len(educations) == 1 else "entries"
        return JobMatchSubScore(
            score=100.0, weight=weight, explanation=f"{len(educations)} education {noun} on file."
        )
    return JobMatchSubScore(
        score=50.0,
        weight=weight,
        explanation="No education history on file; treated as neutral rather than penalized.",
    )


def _keyword_overlap(a: str, b: str) -> bool:
    a_words = {word for word in a.lower().split() if len(word) > 2}
    b_words = {word for word in b.lower().split() if len(word) > 2}
    return bool(a_words & b_words)


def _text_match_score(a: str, b: str) -> float:
    a_lower, b_lower = a.lower(), b.lower()
    if a_lower == b_lower or a_lower in b_lower or b_lower in a_lower:
        return 100.0
    if _keyword_overlap(a_lower, b_lower):
        return 70.0
    return 40.0


def _preference_subscore(career_goal: CareerGoal | None, job: Job) -> JobMatchSubScore:
    weight = WEIGHTS["preference_match"]
    if career_goal is None:
        return JobMatchSubScore(
            score=60.0, weight=weight, explanation="No active career goal set to compare against."
        )

    role_score = _text_match_score(career_goal.target_role, job.title)
    industry_score = 70.0
    if career_goal.target_industry and job.company.industry:
        industry_score = _text_match_score(career_goal.target_industry, job.company.industry)

    score = (role_score + industry_score) / 2
    return JobMatchSubScore(
        score=round(score, 2),
        weight=weight,
        explanation=(
            f"Target role '{career_goal.target_role}' compared against posting title '{job.title}'."
        ),
    )


def _location_subscore(profile: Profile | None, job: Job) -> JobMatchSubScore:
    weight = WEIGHTS["location_match"]
    if job.remote:
        return JobMatchSubScore(
            score=100.0,
            weight=weight,
            explanation="This posting is remote, so it matches any location.",
        )
    if profile is None or not profile.location or not job.location:
        return JobMatchSubScore(
            score=50.0, weight=weight, explanation="Not enough location data to compare."
        )
    matched = _text_match_score(profile.location, job.location)
    # A plain city/region string comparison has no meaningful "shares a keyword" middle ground
    # the way role/industry text does, so collapse the text-match helper's partial-credit tier
    # down to a firmer no-match score here.
    score = matched if matched != 40.0 else 30.0
    return JobMatchSubScore(
        score=score,
        weight=weight,
        explanation=(
            f"Profile location '{profile.location}' compared against posting location "
            f"'{job.location}'."
        ),
    )


def _compute_breakdown(
    *,
    job: Job,
    profile: Profile | None,
    user_skill_ids: set[uuid.UUID],
    experiences: list[Experience],
    educations: list[Education],
    career_goal: CareerGoal | None,
    resume_embedding: list[float] | None,
) -> JobMatchBreakdown:
    return JobMatchBreakdown(
        semantic_similarity=_semantic_similarity_subscore(resume_embedding, job.embedding),
        skill_overlap=_skill_overlap_subscore(user_skill_ids, job.required_skills),
        experience_match=_experience_subscore(
            _years_of_experience(experiences), job.seniority_level
        ),
        education_match=_education_subscore(educations),
        preference_match=_preference_subscore(career_goal, job),
        location_match=_location_subscore(profile, job),
    )


def _overall_score(breakdown: JobMatchBreakdown) -> float:
    total = sum(
        sub_score.score * sub_score.weight
        for sub_score in (
            breakdown.semantic_similarity,
            breakdown.skill_overlap,
            breakdown.experience_match,
            breakdown.education_match,
            breakdown.preference_match,
            breakdown.location_match,
        )
    )
    return round(total, 2)


def _explanation(job: Job, breakdown: JobMatchBreakdown, score: float) -> str:
    components = {
        "semantic similarity": breakdown.semantic_similarity,
        "skill overlap": breakdown.skill_overlap,
        "experience": breakdown.experience_match,
        "education": breakdown.education_match,
        "preference": breakdown.preference_match,
        "location": breakdown.location_match,
    }
    strongest = max(components, key=lambda name: components[name].score * components[name].weight)
    return f"{score:.0f}% match for {job.title} — strongest signal: {strongest}."


async def _latest_resume_embedding(db: AsyncSession, user_id: uuid.UUID) -> list[float] | None:
    result = await db.execute(
        select(Embedding.embedding)
        .join(Resume, Resume.id == Embedding.owner_id)
        .where(
            Embedding.owner_type == "resume",
            Resume.user_id == user_id,
            Resume.deleted_at.is_(None),
            Resume.status == ResumeStatus.COMPLETED,
        )
        .order_by(Embedding.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return list(row) if row is not None else None


async def _candidate_jobs(
    db: AsyncSession, resume_embedding: list[float] | None, *, limit: int
) -> list[Job]:
    """Semantic nearest-neighbor retrieval against the resume embedding narrows the full jobs
    table down to a plausible candidate pool before the more expensive per-job breakdown scoring
    runs — the ANN-then-rerank pattern, not a design ambition to bring in every posting. Falls
    back to the newest active postings when the user has no resume embedding yet (no completed
    resume, or Phase 5 analysis hasn't produced one), same graceful-degradation precedent as
    `find_related_career_paths` returning an empty list rather than erroring."""
    if resume_embedding is not None:
        result = await db.execute(
            select(Job)
            .where(Job.is_active.is_(True), Job.embedding.is_not(None))
            .order_by(Job.embedding.cosine_distance(resume_embedding))
            .limit(limit)
        )
    else:
        result = await db.execute(
            select(Job).where(Job.is_active.is_(True)).order_by(Job.posted_at.desc()).limit(limit)
        )
    return list(result.scalars().all())


async def refresh_job_matches(
    db: AsyncSession, *, user: User, candidate_pool_size: int = CANDIDATE_POOL_SIZE
) -> list[JobMatch]:
    """`POST /api/v1/jobs/match` — recomputes this user's ranked job matches against the current
    candidate pool. Replaces any previously-stored matches for these candidates, same
    cached/recompute-on-demand convention as `compute_and_store_skill_gaps`
    (app/services/skill_gap.py); does not commit, callers own the transaction.
    """
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()

    user_skill_ids: set[uuid.UUID] = set()
    experiences: list[Experience] = []
    educations: list[Education] = []
    if profile is not None:
        skills_result = await db.execute(
            select(UserSkill.skill_id).where(UserSkill.profile_id == profile.id)
        )
        user_skill_ids = set(skills_result.scalars().all())

        exp_result = await db.execute(
            select(Experience).where(
                Experience.profile_id == profile.id, Experience.deleted_at.is_(None)
            )
        )
        experiences = list(exp_result.scalars().all())

        edu_result = await db.execute(
            select(Education).where(
                Education.profile_id == profile.id, Education.deleted_at.is_(None)
            )
        )
        educations = list(edu_result.scalars().all())

    goal_result = await db.execute(
        select(CareerGoal)
        .where(CareerGoal.user_id == user.id, CareerGoal.is_active.is_(True))
        .order_by(CareerGoal.created_at.desc())
    )
    career_goal = goal_result.scalars().first()

    resume_embedding = await _latest_resume_embedding(db, user.id)
    jobs = await _candidate_jobs(db, resume_embedding, limit=candidate_pool_size)

    matches: list[JobMatch] = []
    for job in jobs:
        breakdown = _compute_breakdown(
            job=job,
            profile=profile,
            user_skill_ids=user_skill_ids,
            experiences=experiences,
            educations=educations,
            career_goal=career_goal,
            resume_embedding=resume_embedding,
        )
        score = _overall_score(breakdown)
        match = JobMatch(
            user_id=user.id,
            job_id=job.id,
            match_score=score,
            score_breakdown=breakdown.model_dump(),
            explanation=_explanation(job, breakdown, score),
        )
        match.job = job
        matches.append(match)

    job_ids = [job.id for job in jobs]
    try:
        async with db.begin_nested():
            await db.execute(
                delete(JobMatch).where(JobMatch.user_id == user.id, JobMatch.job_id.in_(job_ids))
            )
            db.add_all(matches)
            await db.flush()
    except IntegrityError:
        return await get_stored_job_matches(db, user_id=user.id)
    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches


async def get_stored_job_matches(db: AsyncSession, *, user_id: uuid.UUID) -> list[JobMatch]:
    result = await db.execute(
        select(JobMatch).where(JobMatch.user_id == user_id).order_by(JobMatch.match_score.desc())
    )
    return list(result.scalars().all())
