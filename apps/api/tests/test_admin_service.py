import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy import delete, select

import app.services.admin as admin_module
from app.core.db import AsyncSessionLocal
from app.models.ai_conversation import AIConversation
from app.models.company import Company
from app.models.job import Job, JobSkill
from app.models.skill import Skill
from app.models.user import Role, User
from app.schemas.admin import AdminJobCreateRequest
from app.services.admin import (
    CompanyNotFoundError,
    SelfDemotionError,
    SkillAlreadyExistsError,
    create_job,
    create_skill,
    get_ai_usage_by_feature,
    get_ai_usage_by_model,
    get_model_metrics,
    get_system_health,
    has_curated_content,
    list_jobs,
    list_skills,
    list_users,
    update_user_role,
)

# Fully additive — never deletes/restores real seeded content. Every fixture creates its own
# uniquely-tagged rows and cleans up only what it created.


@pytest.fixture
async def admin_users() -> AsyncGenerator[tuple[User, User]]:
    """Two real ADMIN users — needed to test that demoting a *different* admin is allowed, only
    self-demotion is blocked."""
    unique = uuid.uuid4().hex[:8]
    acting = User(id=uuid.uuid4(), email=f"admin-a-{unique}@example.com", role=Role.ADMIN)
    other = User(id=uuid.uuid4(), email=f"admin-b-{unique}@example.com", role=Role.ADMIN)
    async with AsyncSessionLocal() as db:
        db.add_all([acting, other])
        await db.commit()

    yield acting, other

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id.in_([acting.id, other.id])))
        await db.commit()


async def test_update_user_role_blocks_self_demotion(admin_users: tuple[User, User]) -> None:
    acting, _other = admin_users
    async with AsyncSessionLocal() as db:
        with pytest.raises(SelfDemotionError):
            await update_user_role(
                db, acting_user=acting, target_user_id=acting.id, new_role=Role.USER
            )


async def test_update_user_role_allows_demoting_a_different_admin(
    admin_users: tuple[User, User],
) -> None:
    acting, other = admin_users
    async with AsyncSessionLocal() as db:
        updated = await update_user_role(
            db, acting_user=acting, target_user_id=other.id, new_role=Role.USER
        )
        await db.commit()
    assert updated is not None
    assert updated.role == Role.USER


async def test_update_user_role_returns_none_for_unknown_user(
    admin_users: tuple[User, User],
) -> None:
    acting, _other = admin_users
    async with AsyncSessionLocal() as db:
        result = await update_user_role(
            db, acting_user=acting, target_user_id=uuid.uuid4(), new_role=Role.USER
        )
    assert result is None


async def test_list_users_pagination_round_trips(admin_users: tuple[User, User]) -> None:
    async with AsyncSessionLocal() as db:
        page_one, cursor = await list_users(db, limit=1, cursor=None, q=None)
        assert len(page_one) == 1
        assert cursor is not None


@pytest.fixture
async def admin_job_company() -> AsyncGenerator[Company]:
    unique = uuid.uuid4().hex[:8]
    company = Company(name=f"Admin Test Co {unique}", slug=f"admin-test-co-{unique}")
    async with AsyncSessionLocal() as db:
        db.add(company)
        await db.commit()

    yield company

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Job).where(Job.company_id == company.id))
        await db.execute(delete(Company).where(Company.id == company.id))
        await db.commit()


async def test_create_job_computes_real_embedding_and_creates_job_skills(
    admin_job_company: Company,
) -> None:
    unique = uuid.uuid4().hex[:8]
    payload = AdminJobCreateRequest(
        company_id=admin_job_company.id,
        title=f"Admin-created Engineer {unique}",
        description="A real job description written by an admin.",
        required_skill_names=[f"Admin Test Skill {unique}"],
    )
    async with AsyncSessionLocal() as db:
        job = await create_job(db, payload=payload)
        await db.commit()
        job_id = job.id

    async with AsyncSessionLocal() as db:
        persisted = await db.get(Job, job_id)
        assert persisted is not None
        assert persisted.embedding is not None
        assert len(persisted.embedding) > 0
        skills_result = await db.execute(select(JobSkill).where(JobSkill.job_id == job_id))
        job_skills = skills_result.scalars().all()
        assert len(job_skills) == 1

    async with AsyncSessionLocal() as db:
        await db.execute(delete(JobSkill).where(JobSkill.job_id == job_id))
        skill_result = await db.execute(
            select(Skill).where(Skill.name == f"Admin Test Skill {unique}")
        )
        skill = skill_result.scalar_one_or_none()
        if skill is not None:
            await db.execute(delete(Skill).where(Skill.id == skill.id))
        await db.commit()


async def test_create_job_dedupes_required_skill_names_resolving_to_the_same_skill(
    admin_job_company: Company,
) -> None:
    """Regression test: 'Python' and 'python' both resolve to the same skill via
    get_or_create_skill's slug-based dedup — without deduping by resolved skill id, this would
    try to insert two JobSkill rows for the same (job_id, skill_id) pair and crash on
    JobSkill's UniqueConstraint at the flush."""
    unique = uuid.uuid4().hex[:8]
    skill_name = f"Dedup Test Skill {unique}"
    payload = AdminJobCreateRequest(
        company_id=admin_job_company.id,
        title=f"Dedup Test Job {unique}",
        description="Test.",
        required_skill_names=[skill_name, skill_name.lower(), skill_name.upper()],
    )
    async with AsyncSessionLocal() as db:
        job = await create_job(db, payload=payload)
        await db.commit()
        job_id = job.id

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(JobSkill).where(JobSkill.job_id == job_id))
            assert len(result.scalars().all()) == 1  # not 3, despite 3 required_skill_names
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(JobSkill).where(JobSkill.job_id == job_id))
            skill_result = await db.execute(select(Skill).where(Skill.name == skill_name))
            skill = skill_result.scalar_one_or_none()
            if skill is not None:
                await db.execute(delete(Skill).where(Skill.id == skill.id))
            await db.commit()


async def test_create_job_raises_for_unknown_company() -> None:
    payload = AdminJobCreateRequest(
        company_id=uuid.uuid4(), title="Ghost Job", description="Ghost description."
    )
    async with AsyncSessionLocal() as db:
        with pytest.raises(CompanyNotFoundError):
            await create_job(db, payload=payload)


async def test_list_jobs_includes_inactive_and_paginates(admin_job_company: Company) -> None:
    async with AsyncSessionLocal() as db:
        db.add_all(
            [
                Job(
                    company_id=admin_job_company.id,
                    title="Active Job",
                    description="Test.",
                    is_active=True,
                ),
                Job(
                    company_id=admin_job_company.id,
                    title="Inactive Job",
                    description="Test.",
                    is_active=False,
                ),
            ]
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        page_one, cursor = await list_jobs(db, limit=1, cursor=None)
        assert len(page_one) == 1
        assert cursor is not None
        page_two, _cursor_two = await list_jobs(db, limit=10, cursor=cursor)
        combined_ids = {j.id for j in page_one} | {j.id for j in page_two}
        titles = {j.title for j in page_one + page_two if j.company_id == admin_job_company.id}
    assert {"Active Job", "Inactive Job"} <= titles
    assert len(combined_ids) == len(page_one) + len(page_two)  # no duplicate across pages


@pytest.fixture
async def curated_and_plain_skill() -> AsyncGenerator[tuple[Skill, Skill]]:
    unique = uuid.uuid4().hex[:8]
    curated = Skill(
        name=f"Curated Skill {unique}",
        slug=f"curated-skill-{unique}",
        seo_summary="A real curated summary.",
    )
    plain = Skill(name=f"Plain Skill {unique}", slug=f"plain-skill-{unique}")
    async with AsyncSessionLocal() as db:
        db.add_all([curated, plain])
        await db.commit()

    yield curated, plain

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Skill).where(Skill.id.in_([curated.id, plain.id])))
        await db.commit()


async def test_has_curated_content_reflects_seo_summary_and_embedding(
    curated_and_plain_skill: tuple[Skill, Skill],
) -> None:
    curated, plain = curated_and_plain_skill
    assert has_curated_content(curated) is True
    assert has_curated_content(plain) is False


async def test_list_skills_pagination_round_trips(
    curated_and_plain_skill: tuple[Skill, Skill],
) -> None:
    async with AsyncSessionLocal() as db:
        page_one, cursor = await list_skills(db, limit=1, cursor=None)
        assert len(page_one) == 1
        assert cursor is not None


async def test_create_skill_then_conflict_on_duplicate() -> None:
    unique = uuid.uuid4().hex[:8]
    name = f"Fresh Skill {unique}"
    async with AsyncSessionLocal() as db:
        skill = await create_skill(db, name=name, category=None)
        await db.commit()
        skill_id = skill.id

    try:
        async with AsyncSessionLocal() as db:
            with pytest.raises(SkillAlreadyExistsError):
                await create_skill(db, name=name, category=None)
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Skill).where(Skill.id == skill_id))
            await db.commit()


async def test_create_skill_survives_concurrent_calls() -> None:
    unique = uuid.uuid4().hex[:8]
    name = f"Race Skill {unique}"

    async def _attempt() -> str:
        async with AsyncSessionLocal() as db:
            try:
                skill = await create_skill(db, name=name, category=None)
                await db.commit()
                return f"won:{skill.id}"
            except SkillAlreadyExistsError:
                return "lost"

    results = await asyncio.gather(_attempt(), _attempt())
    outcomes = sorted(r.split(":")[0] for r in results)
    assert outcomes == ["lost", "won"]

    winner_id = next(r for r in results if r.startswith("won:")).split(":")[1]
    async with AsyncSessionLocal() as db:
        await db.execute(delete(Skill).where(Skill.id == uuid.UUID(winner_id)))
        await db.commit()


@pytest.fixture
async def ai_usage_rows() -> AsyncGenerator[uuid.UUID]:
    unique = uuid.uuid4().hex[:8]
    user = User(id=uuid.uuid4(), email=f"ai-usage-{unique}@example.com", role=Role.USER)
    async with AsyncSessionLocal() as db:
        db.add(user)
        await db.commit()
        db.add_all(
            [
                AIConversation(
                    user_id=user.id,
                    feature=f"test_feature_{unique}",
                    model="test-model-a",
                    prompt_tokens=100,
                    completion_tokens=50,
                    latency_ms=200,
                ),
                AIConversation(
                    user_id=user.id,
                    feature=f"test_feature_{unique}",
                    model="test-model-a",
                    prompt_tokens=200,
                    completion_tokens=100,
                    latency_ms=400,
                ),
            ]
        )
        await db.commit()

    yield user.id

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


async def test_ai_usage_by_feature_and_model_aggregate_correctly(
    ai_usage_rows: uuid.UUID,
) -> None:
    async with AsyncSessionLocal() as db:
        by_feature = await get_ai_usage_by_feature(db, date_from=None, date_to=None)
        by_model = await get_ai_usage_by_model(db, date_from=None, date_to=None)

    feature_row = next(r for r in by_feature if r.call_count >= 2 and r.prompt_tokens == 300)
    assert feature_row.completion_tokens == 150
    assert feature_row.avg_latency_ms == pytest.approx(300.0)

    model_row = next(r for r in by_model if r.model == "test-model-a" and r.prompt_tokens >= 300)
    assert model_row.completion_tokens >= 150


async def test_get_model_metrics_degrades_gracefully_for_missing_and_malformed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    valid_dir = tmp_path / "valid_model" / "1.0.0"
    valid_dir.mkdir(parents=True)
    (valid_dir / "metadata.json").write_text(
        json.dumps({"metric": "roc_auc", "score": 0.9, "training_window": "test"})
    )

    malformed_dir = tmp_path / "malformed_model" / "1.0.0"
    malformed_dir.mkdir(parents=True)
    (malformed_dir / "metadata.json").write_text("{not valid json")

    # "missing_model" has no directory at all.
    monkeypatch.setattr(
        admin_module,
        "_MODEL_VERSIONS",
        {"valid_model": "1.0.0", "malformed_model": "1.0.0", "missing_model": "1.0.0"},
    )
    monkeypatch.setattr(admin_module.registry, "MODELS_DIR", tmp_path)

    entries = get_model_metrics()
    by_name = {e.name: e for e in entries}

    assert by_name["valid_model"].available is True
    assert by_name["valid_model"].score == pytest.approx(0.9)

    assert by_name["malformed_model"].available is False
    assert by_name["malformed_model"].score is None

    assert by_name["missing_model"].available is False
    assert by_name["missing_model"].score is None


async def test_get_system_health_returns_real_connectivity_and_counts() -> None:
    async with AsyncSessionLocal() as db:
        health = await get_system_health(db)
    assert health.database_ok is True
    assert health.redis_ok is True
    assert health.total_users >= 0
    assert health.total_jobs >= 0
    assert health.total_resumes >= 0
