"""Phase 13 — Admin (docs/ROADMAP.md, docs/API.md "### Admin"). Every function here is called
only from routes gated by `Depends(require_role(Role.ADMIN))` (app/core/security.py) — no
additional per-function authorization check, matching that dependency's own stated role as the
one real authorization boundary for this whole feature (docs/SECURITY.md §2).

Deliberately does NOT touch `audit_logs` (reserved for Phase 15, docs/SECURITY.md's own status
line) or compute live model drift (reserved for Phase 14, app/ml/registry.py's own docstring).
"""

import json
import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.pagination import decode_cursor, encode_cursor
from app.core.redis import get_redis
from app.ml import registry
from app.models.ai_conversation import AIConversation
from app.models.company import Company
from app.models.job import Job, JobSkill
from app.models.resume import Resume
from app.models.skill import Skill, slugify
from app.models.user import Role, User
from app.schemas.admin import (
    AdminJobCreateRequest,
    AIUsageByFeature,
    AIUsageByModel,
    ModelMetricsEntry,
    SystemHealthRead,
)
from app.services.embeddings import embed_text
from app.services.skill_taxonomy import get_or_create_skill

# Matches app/services/adzuna_ingestion.py's own `_DESCRIPTION_MAX_CHARS` value/reasoning
# (embed_text's input budget) — kept as a separate local constant since that one is private to
# its own module, not because the value should ever legitimately diverge.
_DESCRIPTION_EMBEDDING_MAX_CHARS = 4000

_MODEL_VERSIONS: dict[str, str] = {
    "job_suitability": settings.model_version_job_suitability,
    "career_recommendation": settings.model_version_career_recommendation,
    "skill_clustering": settings.model_version_skill_clustering,
    "salary_prediction": settings.model_version_salary_prediction,
    "job_category": settings.model_version_job_category,
    "skill_demand_forecast": settings.model_version_skill_demand_forecast,
}


class SelfDemotionError(Exception):
    """Raised when an admin tries to remove their own ADMIN role — there is no other path to
    ADMIN besides direct DB access, so this would be a real, unrecoverable lockout."""


class SkillAlreadyExistsError(Exception):
    """Raised by `create_skill` on a slug collision — unlike `get_or_create_skill`
    (app/services/skill_taxonomy.py), an explicit admin "create" action must surface a
    duplicate as a real conflict, not silently return the existing row."""


class CompanyNotFoundError(Exception):
    pass


# --- Users ----------------------------------------------------------------------------------


async def list_users(
    db: AsyncSession, *, limit: int, cursor: str | None, q: str | None
) -> tuple[list[User], str | None]:
    stmt = select(User)
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q}%"))
    if cursor:
        created_at, last_id, _rank = decode_cursor(cursor)
        stmt = stmt.where(tuple_(User.created_at, User.id) < (created_at, last_id))
    stmt = stmt.order_by(User.created_at.desc(), User.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if len(rows) > limit:
        page = rows[:limit]
        last = page[-1]
        return page, encode_cursor(sort_value=last.created_at, id=last.id)
    return rows, None


async def update_user_role(
    db: AsyncSession, *, acting_user: User, target_user_id: uuid.UUID, new_role: Role
) -> User | None:
    if (
        target_user_id == acting_user.id
        and acting_user.role == Role.ADMIN
        and new_role != Role.ADMIN
    ):
        raise SelfDemotionError("You cannot remove your own admin access.")

    result = await db.execute(select(User).where(User.id == target_user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    user.role = new_role
    await db.flush()
    return user


# --- Jobs -------------------------------------------------------------------------------------


async def list_jobs(
    db: AsyncSession, *, limit: int, cursor: str | None
) -> tuple[list[Job], str | None]:
    stmt = select(Job)
    if cursor:
        created_at, last_id, _rank = decode_cursor(cursor)
        stmt = stmt.where(tuple_(Job.created_at, Job.id) < (created_at, last_id))
    stmt = stmt.order_by(Job.created_at.desc(), Job.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if len(rows) > limit:
        page = rows[:limit]
        last = page[-1]
        return page, encode_cursor(sort_value=last.created_at, id=last.id)
    return rows, None


async def create_job(db: AsyncSession, *, payload: AdminJobCreateRequest) -> Job:
    """Does not commit — the route owns the transaction, matching every ingestion/seed script's
    own "callers own the transaction" convention (see app/services/adzuna_ingestion.py). Leaves
    `source`/`external_id` both `NULL` (admin-authored, not adzuna-sourced) — Postgres treats
    `NULL` as distinct in the `(source, external_id)` unique index, so this never collides with
    an ingested row."""
    company_result = await db.execute(select(Company).where(Company.id == payload.company_id))
    company = company_result.scalar_one_or_none()
    if company is None:
        raise CompanyNotFoundError(f"Company {payload.company_id} not found.")

    job = Job(
        company_id=company.id,
        title=payload.title,
        description=payload.description,
        seniority_level=payload.seniority_level,
        employment_type=payload.employment_type,
        location=payload.location,
        remote=payload.remote,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        currency=payload.currency,
        apply_url=payload.apply_url,
        is_active=True,
        search_category=payload.search_category,
    )
    db.add(job)
    await db.flush()

    # Dedupe by resolved skill id, not just raw name — two different names can resolve to the
    # same skill via get_or_create_skill's own slug-based dedup (e.g. "Python" and "python"),
    # and JobSkill has a UniqueConstraint("job_id", "skill_id") that would otherwise crash this
    # request with an unhandled IntegrityError at the flush below.
    seen_skill_ids: set[uuid.UUID] = set()
    for skill_name in payload.required_skill_names:
        skill = await get_or_create_skill(db, skill_name)
        if skill.id in seen_skill_ids:
            continue
        seen_skill_ids.add(skill.id)
        db.add(JobSkill(job_id=job.id, skill_id=skill.id))

    job.embedding = await embed_text(
        f"{job.title} at {company.name}\n\n{job.description[:_DESCRIPTION_EMBEDDING_MAX_CHARS]}"
    )
    await db.flush()
    return job


# --- Skills -----------------------------------------------------------------------------------


async def list_skills(
    db: AsyncSession, *, limit: int, cursor: str | None
) -> tuple[list[Skill], str | None]:
    stmt = select(Skill)
    if cursor:
        created_at, last_id, _rank = decode_cursor(cursor)
        stmt = stmt.where(tuple_(Skill.created_at, Skill.id) < (created_at, last_id))
    stmt = stmt.order_by(Skill.created_at.desc(), Skill.id.desc()).limit(limit + 1)
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if len(rows) > limit:
        page = rows[:limit]
        last = page[-1]
        return page, encode_cursor(sort_value=last.created_at, id=last.id)
    return rows, None


async def create_skill(db: AsyncSession, *, name: str, category: str | None) -> Skill:
    """A genuinely separate function from `get_or_create_skill` (app/services/skill_taxonomy.py)
    — that function's contract is to *return the existing row* on a match, which is exactly
    wrong for an explicit admin "create" action that should surface a duplicate as a real 409,
    not a silent success. Same SAVEPOINT race-safety shape, different response semantics in both
    branches: the pre-check AND the concurrent-request path both raise
    `SkillAlreadyExistsError`."""
    clean_name = name.strip()
    slug = slugify(clean_name)

    existing_result = await db.execute(select(Skill).where(Skill.slug == slug))
    if existing_result.scalar_one_or_none() is not None:
        raise SkillAlreadyExistsError(f"A skill matching '{clean_name}' already exists.")

    try:
        async with db.begin_nested():
            skill = Skill(name=clean_name, slug=slug, category=category)
            db.add(skill)
            await db.flush()
    except IntegrityError as exc:
        raise SkillAlreadyExistsError(f"A skill matching '{clean_name}' already exists.") from exc
    return skill


def has_curated_content(skill: Skill) -> bool:
    return skill.seo_summary is not None or skill.embedding is not None


# --- AI usage ---------------------------------------------------------------------------------


async def get_ai_usage_by_feature(
    db: AsyncSession, *, date_from: date | None, date_to: date | None
) -> list[AIUsageByFeature]:
    stmt = select(
        AIConversation.feature,
        func.count().label("call_count"),
        func.sum(AIConversation.prompt_tokens).label("prompt_tokens"),
        func.sum(AIConversation.completion_tokens).label("completion_tokens"),
        func.avg(AIConversation.latency_ms).label("avg_latency_ms"),
    ).group_by(AIConversation.feature)
    stmt = _apply_ai_usage_date_filter(stmt, date_from=date_from, date_to=date_to)
    result = await db.execute(stmt.order_by(func.count().desc()))
    return [
        AIUsageByFeature(
            feature=row.feature,
            call_count=row.call_count,
            prompt_tokens=row.prompt_tokens or 0,
            completion_tokens=row.completion_tokens or 0,
            avg_latency_ms=float(row.avg_latency_ms) if row.avg_latency_ms is not None else 0.0,
        )
        for row in result.all()
    ]


async def get_ai_usage_by_model(
    db: AsyncSession, *, date_from: date | None, date_to: date | None
) -> list[AIUsageByModel]:
    stmt = select(
        AIConversation.model,
        func.count().label("call_count"),
        func.sum(AIConversation.prompt_tokens).label("prompt_tokens"),
        func.sum(AIConversation.completion_tokens).label("completion_tokens"),
        func.avg(AIConversation.latency_ms).label("avg_latency_ms"),
    ).group_by(AIConversation.model)
    stmt = _apply_ai_usage_date_filter(stmt, date_from=date_from, date_to=date_to)
    result = await db.execute(stmt.order_by(func.count().desc()))
    return [
        AIUsageByModel(
            model=row.model,
            call_count=row.call_count,
            prompt_tokens=row.prompt_tokens or 0,
            completion_tokens=row.completion_tokens or 0,
            avg_latency_ms=float(row.avg_latency_ms) if row.avg_latency_ms is not None else 0.0,
        )
        for row in result.all()
    ]


def _apply_ai_usage_date_filter(stmt: Any, *, date_from: date | None, date_to: date | None) -> Any:
    if date_from is not None:
        stmt = stmt.where(AIConversation.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AIConversation.created_at <= date_to)
    return stmt


# --- Model metrics -----------------------------------------------------------------------------


def get_model_metrics() -> list[ModelMetricsEntry]:
    """Plain sync function — a handful of small local JSON reads, matching `app/ml/registry.py`/
    `app/ml/inference.py`'s own established convention of not wrapping cheap local-disk model I/O
    in async. Wraps each model's read+parse independently: a missing OR malformed
    `metadata.json` for one model returns `available=False` for just that model, never a 500 for
    the other 5 (the real gap in `inference.py`'s own `_model_mae()` precedent, which only
    guards the missing-file case, not a malformed one)."""
    entries = []
    for name, version in _MODEL_VERSIONS.items():
        path = registry.MODELS_DIR / name / version / "metadata.json"
        try:
            data = json.loads(path.read_text())
            entries.append(
                ModelMetricsEntry(
                    name=name,
                    version=version,
                    available=True,
                    metric=data.get("metric"),
                    score=data.get("score"),
                    training_window=data.get("training_window"),
                    limitations=data.get("limitations"),
                    retrained_at=data.get("retrained_at"),
                )
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            entries.append(ModelMetricsEntry(name=name, version=version, available=False))
    return entries


# --- System health -----------------------------------------------------------------------------


async def get_system_health(db: AsyncSession) -> SystemHealthRead:
    try:
        await db.execute(select(1))
        database_ok = True
    except Exception:
        database_ok = False

    try:
        redis = get_redis()
        await redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    # A failed `select(1)` above means this session is now in a broken/aborted state — every
    # further query on it would raise too, not degrade gracefully. Skip them entirely rather
    # than letting an exception propagate out of an otherwise-successful health check.
    total_users = total_jobs = total_resumes = 0
    if database_ok:
        total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        total_jobs = (await db.execute(select(func.count()).select_from(Job))).scalar_one()
        total_resumes = (await db.execute(select(func.count()).select_from(Resume))).scalar_one()

    return SystemHealthRead(
        database_ok=database_ok,
        redis_ok=redis_ok,
        total_users=total_users,
        total_jobs=total_jobs,
        total_resumes=total_resumes,
    )
