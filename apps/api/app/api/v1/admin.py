import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.pagination import InvalidCursorError
from app.core.security import require_role
from app.models.user import Role, User
from app.schemas.admin import (
    AdminJobCreateRequest,
    AdminJobRead,
    AdminSkillCreateRequest,
    AdminSkillRead,
    AdminUserRead,
    AdminUserUpdateRequest,
    AIUsageRead,
    ModelMetricsRead,
    SystemHealthRead,
)
from app.schemas.envelope import Envelope, meta_from_request
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

router = APIRouter(prefix="/admin", tags=["admin"])

AdminDep = Annotated[User, Depends(require_role(Role.ADMIN))]
DbDep = Annotated[AsyncSession, Depends(get_db)]

# Every route requires Role.ADMIN (docs/SECURITY.md §2) — require_role wraps get_current_user,
# so `AdminDep` already resolves to the fully-loaded acting User, no separate auth dependency
# needed alongside it. No Idempotency-Key/rate-limit on any route here — no LLM call anywhere in
# this feature.


@router.get("/users", response_model=Envelope[list[AdminUserRead]])
async def list_admin_users(
    request: Request,
    _admin: AdminDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> Envelope[list[AdminUserRead]]:
    try:
        users, next_cursor = await list_users(db, limit=limit, cursor=cursor, q=q)
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Envelope(
        data=[AdminUserRead.model_validate(u) for u in users],
        meta=meta_from_request(request, next_cursor=next_cursor),
    )


@router.patch("/users/{user_id}", response_model=Envelope[AdminUserRead])
async def update_admin_user(
    request: Request,
    user_id: uuid.UUID,
    payload: AdminUserUpdateRequest,
    admin: AdminDep,
    db: DbDep,
) -> Envelope[AdminUserRead]:
    try:
        user = await update_user_role(
            db, acting_user=admin, target_user_id=user_id, new_role=payload.role
        )
    except SelfDemotionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    await db.commit()
    return Envelope(data=AdminUserRead.model_validate(user), meta=meta_from_request(request))


@router.get("/jobs", response_model=Envelope[list[AdminJobRead]])
async def list_admin_jobs(
    request: Request,
    _admin: AdminDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> Envelope[list[AdminJobRead]]:
    try:
        jobs, next_cursor = await list_jobs(db, limit=limit, cursor=cursor)
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Envelope(
        data=[AdminJobRead.model_validate(j) for j in jobs],
        meta=meta_from_request(request, next_cursor=next_cursor),
    )


@router.post("/jobs", response_model=Envelope[AdminJobRead], status_code=status.HTTP_201_CREATED)
async def create_admin_job(
    request: Request, payload: AdminJobCreateRequest, _admin: AdminDep, db: DbDep
) -> Envelope[AdminJobRead]:
    try:
        job = await create_job(db, payload=payload)
    except CompanyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(job, attribute_names=["company"])
    return Envelope(data=AdminJobRead.model_validate(job), meta=meta_from_request(request))


@router.get("/skills", response_model=Envelope[list[AdminSkillRead]])
async def list_admin_skills(
    request: Request,
    _admin: AdminDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> Envelope[list[AdminSkillRead]]:
    try:
        skills, next_cursor = await list_skills(db, limit=limit, cursor=cursor)
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    data = [
        AdminSkillRead(
            id=s.id,
            name=s.name,
            slug=s.slug,
            category=s.category,
            has_curated_content=has_curated_content(s),
            created_at=s.created_at,
        )
        for s in skills
    ]
    return Envelope(data=data, meta=meta_from_request(request, next_cursor=next_cursor))


@router.post(
    "/skills", response_model=Envelope[AdminSkillRead], status_code=status.HTTP_201_CREATED
)
async def create_admin_skill(
    request: Request, payload: AdminSkillCreateRequest, _admin: AdminDep, db: DbDep
) -> Envelope[AdminSkillRead]:
    try:
        skill = await create_skill(db, name=payload.name, category=payload.category)
    except SkillAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    data = AdminSkillRead(
        id=skill.id,
        name=skill.name,
        slug=skill.slug,
        category=skill.category,
        has_curated_content=has_curated_content(skill),
        created_at=skill.created_at,
    )
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("/ai-usage", response_model=Envelope[AIUsageRead])
async def get_admin_ai_usage(
    request: Request,
    _admin: AdminDep,
    db: DbDep,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Envelope[AIUsageRead]:
    data = AIUsageRead(
        by_feature=await get_ai_usage_by_feature(db, date_from=date_from, date_to=date_to),
        by_model=await get_ai_usage_by_model(db, date_from=date_from, date_to=date_to),
    )
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("/model-metrics", response_model=Envelope[ModelMetricsRead])
async def get_admin_model_metrics(request: Request, _admin: AdminDep) -> Envelope[ModelMetricsRead]:
    data = ModelMetricsRead(models=get_model_metrics())
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("/system-health", response_model=Envelope[SystemHealthRead])
async def get_admin_system_health(
    request: Request, _admin: AdminDep, db: DbDep
) -> Envelope[SystemHealthRead]:
    data = await get_system_health(db)
    return Envelope(data=data, meta=meta_from_request(request))
