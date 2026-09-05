import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.models.career_goal import CareerGoal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.company import Company
from app.models.job import Job, JobSkill
from app.models.job_match import Application, ApplicationStatus, JobMatch
from app.models.learning_path import LearningPath, LearningPathItem, RoadmapPhase
from app.models.market_data import SalaryData, SkillDemand
from app.models.resume import FileType, Resume, ResumeStatus
from app.models.skill import Skill
from app.models.skill_gap import GapLevel, SkillGap
from app.models.user import Role, User
from app.scripts.aggregate_market_data import MIN_PERIOD_COUNT
from app.services.analytics import (
    _avg_associated_salary_by_skill,
    _top_growing_skills,
    _trending_career_paths,
    get_candidate_dashboard,
    get_skill_analytics,
)

# Fully additive — never deletes/restores real seeded content (unlike interview tests'
# isolated_technical_bank): Skill/Job/CareerPath are too deeply cross-referenced by other real
# data (UserSkill, JobSkill, CareerPathSkill, SkillGap, LearningPathItem) to safely delete-and-
# restore. Every fixture here creates its own uniquely-tagged rows and asserts by searching the
# real, catalog-wide result set for its own entities by id — never asserting on the whole list's
# exact shape, since real seeded data coexists in every query this module touches.

_FAR_PAST_PERIOD = date(2020, 1, 6)  # a Monday, far from any real seeded period


@pytest.fixture
async def two_growth_skills() -> AsyncGenerator[tuple[uuid.UUID, uuid.UUID]]:
    """One skill with real, eligible current-period data; one with a deliberately noisy,
    ineligible current-period count (`demand_count` below `MIN_PERIOD_COUNT`) but a high
    `growth_rate` already stored — the exact scenario the Plan-agent critique flagged as a real
    gap in a naive top-N-by-growth_rate query."""
    unique = uuid.uuid4().hex[:8]
    eligible = Skill(name=f"Eligible Skill {unique}", slug=f"eligible-skill-{unique}")
    thin = Skill(name=f"Thin Skill {unique}", slug=f"thin-skill-{unique}")
    async with AsyncSessionLocal() as db:
        db.add_all([eligible, thin])
        await db.flush()
        db.add_all(
            [
                SkillDemand(
                    skill_id=eligible.id,
                    demand_count=MIN_PERIOD_COUNT + 7,
                    growth_rate=2.0,
                    period=_FAR_PAST_PERIOD,
                ),
                SkillDemand(
                    skill_id=thin.id,
                    demand_count=MIN_PERIOD_COUNT - 1,
                    growth_rate=5.0,  # noisy but real-looking — must be excluded
                    period=_FAR_PAST_PERIOD,
                ),
            ]
        )
        await db.commit()
        eligible_id, thin_id = eligible.id, thin.id

    yield eligible_id, thin_id

    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(SkillDemand).where(SkillDemand.skill_id.in_([eligible_id, thin_id]))
        )
        await db.execute(delete(Skill).where(Skill.id.in_([eligible_id, thin_id])))
        await db.commit()


async def test_top_growing_skills_excludes_thin_current_period(
    two_growth_skills: tuple[uuid.UUID, uuid.UUID],
) -> None:
    eligible_id, thin_id = two_growth_skills
    async with AsyncSessionLocal() as db:
        results = await _top_growing_skills(db)
    result_ids = {r.skill_id for r in results}
    assert eligible_id in result_ids
    assert thin_id not in result_ids  # the real bug this regression test targets


@pytest.fixture
async def career_paths_with_null_handling() -> AsyncGenerator[
    tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]
]:
    """`path_partial` requires one skill with a real growth_rate and one with none at all;
    `path_all_null` requires only a skill with no SkillDemand row whatsoever. Returns
    (path_partial_id, path_all_null_id, skill_with_growth_id, skill_no_growth_id)."""
    unique = uuid.uuid4().hex[:8]
    skill_with_growth = Skill(name=f"Growth Skill {unique}", slug=f"growth-skill-{unique}")
    skill_no_growth = Skill(name=f"No Growth Skill {unique}", slug=f"no-growth-skill-{unique}")
    async with AsyncSessionLocal() as db:
        db.add_all([skill_with_growth, skill_no_growth])
        await db.flush()
        db.add(
            SkillDemand(
                skill_id=skill_with_growth.id,
                demand_count=MIN_PERIOD_COUNT + 7,
                growth_rate=4.0,
                period=_FAR_PAST_PERIOD,
            )
        )

        path_partial = CareerPath(
            slug=f"test-path-partial-{unique}",
            title=f"Test Path Partial {unique}",
            summary="Test.",
            description_md="Test.",
            related_job_titles=[],
            published=True,
        )
        path_all_null = CareerPath(
            slug=f"test-path-all-null-{unique}",
            title=f"Test Path All Null {unique}",
            summary="Test.",
            description_md="Test.",
            related_job_titles=[],
            published=True,
        )
        db.add_all([path_partial, path_all_null])
        await db.flush()
        db.add_all(
            [
                CareerPathSkill(
                    career_path_id=path_partial.id,
                    skill_id=skill_with_growth.id,
                    weight=5,
                    is_core=False,
                ),
                CareerPathSkill(
                    career_path_id=path_partial.id,
                    skill_id=skill_no_growth.id,
                    weight=5,
                    is_core=False,
                ),
                CareerPathSkill(
                    career_path_id=path_all_null.id,
                    skill_id=skill_no_growth.id,
                    weight=5,
                    is_core=False,
                ),
            ]
        )
        await db.commit()
        ids = (path_partial.id, path_all_null.id, skill_with_growth.id, skill_no_growth.id)

    yield ids

    path_partial_id, path_all_null_id, growth_id, no_growth_id = ids
    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(CareerPathSkill).where(
                CareerPathSkill.career_path_id.in_([path_partial_id, path_all_null_id])
            )
        )
        await db.execute(
            delete(CareerPath).where(CareerPath.id.in_([path_partial_id, path_all_null_id]))
        )
        await db.execute(delete(SkillDemand).where(SkillDemand.skill_id == growth_id))
        await db.execute(delete(Skill).where(Skill.id.in_([growth_id, no_growth_id])))
        await db.commit()


async def test_trending_career_paths_averages_only_non_null_growth_rates(
    career_paths_with_null_handling: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    path_partial_id, path_all_null_id, _growth_id, _no_growth_id = career_paths_with_null_handling
    async with AsyncSessionLocal() as db:
        results = await _trending_career_paths(db)
    by_id = {r.career_path_id: r for r in results}

    assert path_partial_id in by_id
    # Averaged over ONLY the one skill with a real rate (4.0), never coerced-to-0 for the other.
    assert by_id[path_partial_id].growth_rate == pytest.approx(4.0)

    # Zero eligible skills -> excluded from the ranking entirely, never shown as growth_rate=0.
    assert path_all_null_id not in by_id


@pytest.fixture
async def salary_join_fixture() -> AsyncGenerator[uuid.UUID]:
    """Two jobs share one (category, seniority) pair (must be deduplicated, not double-counted);
    a third job has a NULL seniority_level in a different category (must still match via
    `IS NOT DISTINCT FROM`, not be silently dropped by a plain `=` join)."""
    unique = uuid.uuid4().hex[:8]
    category_a = f"test-cat-a-{unique}"
    category_b = f"test-cat-b-{unique}"
    skill = Skill(name=f"Salary Test Skill {unique}", slug=f"salary-test-skill-{unique}")

    async with AsyncSessionLocal() as db:
        db.add(skill)
        await db.flush()
        company = Company(
            name=f"Test Co {unique}", slug=f"test-co-salary-{unique}", industry="Software"
        )
        db.add(company)
        await db.flush()

        job_a1 = Job(
            company_id=company.id,
            title="A1",
            description="Test.",
            seniority_level="Mid-level",
            remote=False,
            is_active=True,
            search_category=category_a,
        )
        job_a2 = Job(
            company_id=company.id,
            title="A2",
            description="Test.",
            seniority_level="Mid-level",
            remote=False,
            is_active=True,
            search_category=category_a,
        )
        job_b = Job(
            company_id=company.id,
            title="B",
            description="Test.",
            seniority_level=None,
            remote=False,
            is_active=True,
            search_category=category_b,
        )
        db.add_all([job_a1, job_a2, job_b])
        await db.flush()
        db.add_all(
            [
                JobSkill(job_id=job_a1.id, skill_id=skill.id),
                JobSkill(job_id=job_a2.id, skill_id=skill.id),
                JobSkill(job_id=job_b.id, skill_id=skill.id),
            ]
        )
        db.add_all(
            [
                SalaryData(
                    job_title=category_a,
                    seniority_level="Mid-level",
                    p25=90_000,
                    p50=100_000,
                    p75=110_000,
                    period=_FAR_PAST_PERIOD,
                ),
                SalaryData(
                    job_title=category_b,
                    seniority_level=None,
                    p25=45_000,
                    p50=50_000,
                    p75=55_000,
                    period=_FAR_PAST_PERIOD,
                ),
            ]
        )
        await db.commit()
        skill_id, company_id = skill.id, company.id
        job_ids = [job_a1.id, job_a2.id, job_b.id]

    yield skill_id

    async with AsyncSessionLocal() as db:
        await db.execute(
            delete(SalaryData).where(SalaryData.job_title.in_([category_a, category_b]))
        )
        await db.execute(delete(JobSkill).where(JobSkill.job_id.in_(job_ids)))
        await db.execute(delete(Job).where(Job.id.in_(job_ids)))
        await db.execute(delete(Company).where(Company.id == company_id))
        await db.execute(delete(Skill).where(Skill.id == skill_id))
        await db.commit()


async def test_avg_associated_salary_deduplicates_and_handles_null_seniority(
    salary_join_fixture: uuid.UUID,
) -> None:
    skill_id = salary_join_fixture
    async with AsyncSessionLocal() as db:
        result = await _avg_associated_salary_by_skill(db)
    # Two distinct (category, seniority) pairs — (category_a, "Mid-level") appearing once
    # despite 2 jobs sharing it, plus (category_b, None) matched via IS NOT DISTINCT FROM.
    # (100_000 + 50_000) / 2 = 75_000 — if the fan-out bug were present, category_a would count
    # twice: (100_000 + 100_000 + 50_000) / 3 = 83_333.33, a different, wrong number.
    assert result[skill_id] == pytest.approx(75_000.0)


async def test_get_skill_analytics_includes_the_test_skill_with_correct_values(
    salary_join_fixture: uuid.UUID,
) -> None:
    skill_id = salary_join_fixture
    async with AsyncSessionLocal() as db:
        data = await get_skill_analytics(db, sort="avg_associated_salary", limit=1000)
    row = next(r for r in data.rows if r.skill_id == skill_id)
    assert row.avg_associated_salary == pytest.approx(75_000.0)


@pytest.fixture
async def analytics_user() -> AsyncGenerator[User]:
    user = User(id=uuid.uuid4(), email=f"analytics-test-{uuid.uuid4()}@example.com", role=Role.USER)
    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.commit()

    yield user

    async with AsyncSessionLocal() as db:
        # Cascades to Resume/CareerGoal/LearningPath(+Items)/JobMatch/Application, all FK
        # ON DELETE CASCADE to users.id.
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


async def test_candidate_dashboard_is_empty_but_never_crashes_for_a_brand_new_user(
    analytics_user: User,
) -> None:
    async with AsyncSessionLocal() as db:
        dashboard = await get_candidate_dashboard(db, user_id=analytics_user.id)

    assert dashboard.resume.status is None
    assert dashboard.resume.overall_score is None
    assert dashboard.skill_gaps is None
    assert dashboard.interviews.total_completed == 0
    assert dashboard.interviews.average_overall_score is None
    assert dashboard.roadmap is None
    assert dashboard.applications.total_matches == 0
    assert dashboard.applications.saved == 0


@pytest.fixture
async def dashboard_full_fixture(
    analytics_user: User,
) -> AsyncGenerator[dict[str, uuid.UUID | str]]:
    """A user with real data in every dashboard section, including the two scenarios the
    Plan-agent critique specifically called out: two simultaneously-`is_active` CareerGoals (must
    resolve to the more recent one, not crash on `scalar_one_or_none()`), and a roadmap for a
    *different* target_role than the active goal (must show the most-recently-updated roadmap
    regardless, per the plan's deliberate design decision)."""
    unique = uuid.uuid4().hex[:8]
    user = analytics_user

    async with AsyncSessionLocal() as db:
        db.add(
            Resume(
                user_id=user.id,
                file_url="https://example.com/r.pdf",
                file_name="r.pdf",
                file_type=FileType.PDF,
                status=ResumeStatus.COMPLETED,
                overall_score=78.25,
            )
        )

        skill = Skill(name=f"Dash Skill {unique}", slug=f"dash-skill-{unique}")
        db.add(skill)
        await db.flush()

        older_path = CareerPath(
            slug=f"dash-older-{unique}",
            title=f"Dash Older {unique}",
            summary="Test.",
            description_md="Test.",
            related_job_titles=[],
            published=True,
        )
        newer_path = CareerPath(
            slug=f"dash-newer-{unique}",
            title=f"Dash Newer {unique}",
            summary="Test.",
            description_md="Test.",
            related_job_titles=[],
            published=True,
        )
        db.add_all([older_path, newer_path])
        await db.flush()

        # Two simultaneously-active goals — the newer one must win. Explicit created_at values:
        # both inserts happen in the same transaction, and Postgres's now() is transaction-time,
        # not statement-time, so relying on server_default here would give both rows the exact
        # same timestamp and make the "most recent" tie-break arbitrary.
        db.add(
            CareerGoal(
                user_id=user.id,
                target_role=older_path.slug,
                is_active=True,
                created_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        await db.flush()
        db.add(
            CareerGoal(
                user_id=user.id,
                target_role=newer_path.slug,
                is_active=True,
                created_at=datetime(2020, 1, 2, tzinfo=UTC),
            )
        )

        # Stored gaps for BOTH roles — only the newer role's gaps should surface.
        db.add(
            SkillGap(
                user_id=user.id,
                skill_id=skill.id,
                target_role=older_path.slug,
                gap_level=GapLevel.STRONG,
                priority=1,
            )
        )
        db.add(
            SkillGap(
                user_id=user.id,
                skill_id=skill.id,
                target_role=newer_path.slug,
                gap_level=GapLevel.MISSING,
                priority=10,
            )
        )

        # A roadmap for the OLDER role — must still be shown (most-recently-updated wins, not
        # tied to whichever goal is currently active).
        roadmap = LearningPath(user_id=user.id, target_role=older_path.slug)
        db.add(roadmap)
        await db.flush()
        db.add(
            LearningPathItem(
                learning_path_id=roadmap.id,
                skill_id=skill.id,
                phase=RoadmapPhase.FOUNDATIONS,
                order_index=0,
                completed=True,
            )
        )

        company = Company(name=f"Dash Co {unique}", slug=f"dash-co-{unique}", industry="Software")
        db.add(company)
        await db.flush()
        job = Job(company_id=company.id, title="Dash Job", description="Test.", is_active=True)
        db.add(job)
        await db.flush()
        db.add(
            JobMatch(
                user_id=user.id, job_id=job.id, match_score=80, score_breakdown={}, explanation="x"
            )
        )
        db.add(Application(user_id=user.id, job_id=job.id, status=ApplicationStatus.APPLIED))

        await db.commit()
        ids: dict[str, uuid.UUID | str] = {
            "skill_id": skill.id,
            "older_path_id": older_path.id,
            "newer_path_id": newer_path.id,
            "newer_path_slug": newer_path.slug,
            "company_id": company.id,
            "job_id": job.id,
        }

    yield ids

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Job).where(Job.id == ids["job_id"]))
        await db.execute(delete(Company).where(Company.id == ids["company_id"]))
        await db.execute(
            delete(CareerPath).where(
                CareerPath.id.in_([ids["older_path_id"], ids["newer_path_id"]])
            )
        )
        await db.execute(delete(Skill).where(Skill.id == ids["skill_id"]))
        await db.commit()


async def test_candidate_dashboard_composes_every_section_correctly(
    analytics_user: User, dashboard_full_fixture: dict[str, uuid.UUID | str]
) -> None:
    async with AsyncSessionLocal() as db:
        dashboard = await get_candidate_dashboard(db, user_id=analytics_user.id)

    assert dashboard.resume.status == ResumeStatus.COMPLETED
    assert dashboard.resume.overall_score == pytest.approx(78.25)

    assert dashboard.skill_gaps is not None
    # The more-recently-created active CareerGoal must win, not the older one.
    assert dashboard.skill_gaps.target_role == dashboard_full_fixture["newer_path_slug"]
    assert dashboard.skill_gaps.missing == 1
    assert dashboard.skill_gaps.strong == 0  # the older role's gap must not leak in

    assert dashboard.roadmap is not None
    assert dashboard.roadmap.completed_items == 1
    assert dashboard.roadmap.total_items == 1

    assert dashboard.applications.total_matches == 1
    assert dashboard.applications.applied == 1
    assert dashboard.applications.saved == 0
