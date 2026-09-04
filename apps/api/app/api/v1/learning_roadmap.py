import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.roadmap_overview import generate_overview
from app.core.db import get_db
from app.core.idempotency import get_cached_response, reserve, store_response
from app.core.rate_limit import RateLimitError, check_ai_rate_limit
from app.core.security import get_current_user
from app.models.career_path import CareerPath
from app.models.learning_path import LearningPath, LearningPathItem
from app.models.skill_learning_resource import SkillLearningResource
from app.models.user import User
from app.schemas.career_path import CareerPathRead
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.learning_roadmap import (
    LearningPathItemRead,
    LearningPathItemUpdate,
    LearningRoadmapProgress,
    LearningRoadmapRead,
    SkillLearningResourceRead,
)
from app.schemas.skill import SkillRead
from app.services.ai_conversations import AIFeature, log_conversation
from app.services.career_paths import CareerPathNotFoundError, resolve_career_path
from app.services.learning_roadmap import (
    delete_learning_path,
    generate_learning_path,
    get_learning_path,
    get_learning_resources_by_skill,
    get_ordered_items,
    get_owned_learning_path_item,
    set_item_completed,
)

router = APIRouter(prefix="/learning-roadmap", tags=["learning-roadmap"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

# Namespaces this route's Idempotency-Key cache separately from any other AI route reusing
# app.core.idempotency — see that module's docstring (Phase 9).
_IDEMPOTENCY_SCOPE = "learning_roadmap"


def _build_item_read(
    item: LearningPathItem, resources: list[tuple[SkillLearningResource, str | None]]
) -> LearningPathItemRead:
    return LearningPathItemRead(
        id=item.id,
        skill=SkillRead.model_validate(item.skill),
        phase=item.phase,
        order_index=item.order_index,
        completed=item.completed,
        completed_at=item.completed_at,
        resources=[
            SkillLearningResourceRead(
                id=resource.id,
                title=resource.title,
                url=resource.url,
                resource_type=resource.resource_type,
                estimated_hours=resource.estimated_hours,
                resource_slug=slug,
            )
            for resource, slug in resources
        ],
    )


async def _build_roadmap_response(
    db: DbDep, learning_path: LearningPath, career_path: CareerPath
) -> LearningRoadmapRead:
    items = await get_ordered_items(db, learning_path.id)
    resources_by_skill = await get_learning_resources_by_skill(
        db, [item.skill_id for item in items]
    )
    item_reads = [
        _build_item_read(item, resources_by_skill.get(item.skill_id, [])) for item in items
    ]
    completed_count = sum(1 for item in items if item.completed)

    return LearningRoadmapRead(
        id=learning_path.id,
        target_role=learning_path.target_role,
        career_path=CareerPathRead.model_validate(career_path),
        overview=learning_path.overview,
        status=learning_path.status,
        generated_at=learning_path.generated_at,
        items=item_reads,
        progress=LearningRoadmapProgress(completed=completed_count, total=len(items)),
    )


async def _resolve_career_path_or_404(db: DbDep, target_role: str) -> CareerPath:
    try:
        return await resolve_career_path(db, target_role)
    except CareerPathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=Envelope[LearningRoadmapRead])
async def get_roadmap(
    request: Request,
    user: UserDep,
    db: DbDep,
    target_role: str = Query(..., min_length=1, max_length=255),
) -> Envelope[LearningRoadmapRead]:
    """Read-only — returns the stored roadmap for (user, target_role). Deliberately does NOT
    auto-generate on first read like `GET /skills/gaps` does: that route's underlying
    computation is free/deterministic, this route's generation has a real LLM cost component
    (app/ai/roadmap_overview.py), and auto-firing a paid LLM call from a GET with no
    Idempotency-Key/rate-limit protection would reopen exactly the AI-cost-control gap Phase 9
    closed for RAG. Call `POST /generate` first."""
    career_path = await _resolve_career_path_or_404(db, target_role)
    learning_path = await get_learning_path(db, user_id=user.id, target_role=career_path.slug)
    if learning_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No roadmap has been generated yet for this role.",
        )
    data = await _build_roadmap_response(db, learning_path, career_path)
    return Envelope(data=data, meta=meta_from_request(request))


@router.post("/generate", response_model=Envelope[LearningRoadmapRead])
async def generate_roadmap(
    request: Request,
    user: UserDep,
    db: DbDep,
    target_role: str = Query(..., min_length=1, max_length=255),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[LearningRoadmapRead]:
    """The only route that runs the sequencing algorithm + the bounded LLM overview call
    (docs/AI_ARCHITECTURE.md §8's Learning Planner). Requires Idempotency-Key and is
    rate-limited — reuses the exact same infra Phase 9 built for `/rag/query`, the first real
    second consumer of that module. Full control-flow mirrors `app/api/v1/rag.py`'s route
    exactly (cache check -> rate limit -> reserve -> work -> commit -> store), with one
    deliberate difference: the LLM overview call can fail without this route ever seeing an
    exception for it (app/ai/roadmap_overview.py swallows it internally) — generation still
    succeeds and commits even when the narrative doesn't."""
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key header is required."
        )
    user_id = str(user.id)

    cached = await get_cached_response(_IDEMPOTENCY_SCOPE, user_id, idempotency_key)
    if cached is not None:
        return Envelope(
            data=LearningRoadmapRead.model_validate(cached), meta=meta_from_request(request)
        )

    try:
        rate_limit = await check_ai_rate_limit(user_id)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI features are temporarily unavailable. Please try again shortly.",
        ) from exc
    if not rate_limit.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests. Please slow down.",
            headers={"Retry-After": str(max(1, rate_limit.retry_after_seconds))},
        )

    claimed = await reserve(_IDEMPOTENCY_SCOPE, user_id, idempotency_key)
    if not claimed:
        cached = await get_cached_response(_IDEMPOTENCY_SCOPE, user_id, idempotency_key)
        if cached is not None:
            return Envelope(
                data=LearningRoadmapRead.model_validate(cached), meta=meta_from_request(request)
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A request with this Idempotency-Key is already being processed.",
        )

    career_path = await _resolve_career_path_or_404(db, target_role)
    learning_path, sequenced = await generate_learning_path(db, user=user, career_path=career_path)

    overview_result = await generate_overview(career_path.title, sequenced)
    if overview_result is not None:
        overview_text, llm_result = overview_result
        learning_path.overview = overview_text
        await log_conversation(
            db,
            user_id=user.id,
            feature=AIFeature.LEARNING_ROADMAP,
            result=llm_result,
            prompt_name="roadmap_overview",
            prompt_version="v1",
        )

    await db.commit()

    data = await _build_roadmap_response(db, learning_path, career_path)
    await store_response(_IDEMPOTENCY_SCOPE, user_id, idempotency_key, data.model_dump(mode="json"))

    return Envelope(data=data, meta=meta_from_request(request))


@router.patch("/items/{item_id}", response_model=Envelope[LearningRoadmapRead])
async def update_roadmap_item(
    request: Request,
    item_id: uuid.UUID,
    payload: LearningPathItemUpdate,
    user: UserDep,
    db: DbDep,
) -> Envelope[LearningRoadmapRead]:
    """Toggle one item's completion — ownership-checked via the parent `learning_path.user_id`
    (ai/rate-limit-free, cheap DB write, auth only). Returns the full roadmap, not just the
    updated item, so the frontend can refresh its whole progress view (including a possible
    `status` auto-transition) from one response rather than reconciling partial state locally."""
    item = await get_owned_learning_path_item(db, item_id=item_id, user_id=user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap item not found.")

    learning_path = await set_item_completed(db, item=item, completed=payload.completed)
    career_path = await _resolve_career_path_or_404(db, learning_path.target_role)
    await db.commit()

    data = await _build_roadmap_response(db, learning_path, career_path)
    return Envelope(data=data, meta=meta_from_request(request))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roadmap(
    user: UserDep,
    db: DbDep,
    target_role: str = Query(..., min_length=1, max_length=255),
) -> None:
    """Soft-deletes the active roadmap for (user, target_role) — the real delete-and-start-over
    path that justifies `LearningPath`'s `SoftDeleteMixin`/partial-unique-index existing at
    all."""
    career_path = await _resolve_career_path_or_404(db, target_role)
    deleted = await delete_learning_path(db, user_id=user.id, target_role=career_path.slug)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active roadmap to delete for this role.",
        )
    await db.commit()
