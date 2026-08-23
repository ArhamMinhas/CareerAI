from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.career_path import CareerPath
from app.models.skill import Skill
from app.models.skill_gap import GapLevel, SkillGap
from app.models.user import User
from app.schemas.career_path import CareerPathRead
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.skill import SkillCareerPathRef, SkillDetailRead, SkillRead
from app.schemas.skill_gap import SkillGapItemRead, SkillGapsResponse, SkillGapSummary
from app.services.career_paths import CareerPathNotFoundError, resolve_career_path
from app.services.skill_gap import compute_and_store_skill_gaps, get_stored_skill_gaps
from app.services.skills import (
    find_career_paths_requiring_skill,
    find_related_skills,
    get_skill_by_id_or_slug,
)

router = APIRouter(prefix="/skills", tags=["skills"])


def _build_gaps_response(career_path: CareerPath, gaps: list[SkillGap]) -> SkillGapsResponse:
    items = sorted(
        (SkillGapItemRead.model_validate(gap) for gap in gaps),
        key=lambda item: item.priority,
        reverse=True,
    )
    summary = SkillGapSummary()
    for item in items:
        setattr(summary, item.gap_level.value, getattr(summary, item.gap_level.value) + 1)
    recommended_next = [
        item for item in items if item.gap_level in (GapLevel.MISSING, GapLevel.WEAK)
    ][:5]
    return SkillGapsResponse(
        target_role=career_path.title,
        career_path=CareerPathRead.model_validate(career_path),
        summary=summary,
        gaps=items,
        recommended_next=recommended_next,
    )


@router.get("", response_model=Envelope[list[SkillRead]])
async def search_skills(
    request: Request,
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = Query(default=None, max_length=255),
) -> Envelope[list[SkillRead]]:
    """Autocomplete for manual skill entry (Phase 3). The full taxonomy browse/gap-analysis
    catalog (docs/API.md §5) is Phase 6 — this only needs to answer "does a skill matching
    this text already exist" for the profile skills form."""
    stmt = select(Skill).order_by(Skill.name).limit(20)
    if q:
        stmt = select(Skill).where(Skill.name.ilike(f"%{q}%")).order_by(Skill.name).limit(20)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return Envelope(
        data=[SkillRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.get("/gaps", response_model=Envelope[SkillGapsResponse])
async def get_skill_gaps(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    target_role: str = Query(..., min_length=1, max_length=255),
) -> Envelope[SkillGapsResponse]:
    """Reads the current user's cached gap analysis against `target_role`, computing it once
    automatically on first read (mirrors resume analysis: initial computation is automatic,
    `POST /gaps/refresh` is for recomputing after the user's skills change) — see
    docs/API.md §5."""
    try:
        career_path = await resolve_career_path(db, target_role)
    except CareerPathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    gaps = await get_stored_skill_gaps(db, user_id=user.id, career_path_slug=career_path.slug)
    if not gaps:
        gaps = await compute_and_store_skill_gaps(db, user=user, career_path=career_path)
        await db.commit()

    return Envelope(data=_build_gaps_response(career_path, gaps), meta=meta_from_request(request))


@router.post("/gaps/refresh", response_model=Envelope[SkillGapsResponse])
async def refresh_skill_gaps(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    target_role: str = Query(..., min_length=1, max_length=255),
) -> Envelope[SkillGapsResponse]:
    """Forces a fresh recomputation — call after adding/editing skills so the cached gap rows
    reflect the current profile rather than waiting for the next unrelated GET."""
    try:
        career_path = await resolve_career_path(db, target_role)
    except CareerPathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    gaps = await compute_and_store_skill_gaps(db, user=user, career_path=career_path)
    await db.commit()

    return Envelope(data=_build_gaps_response(career_path, gaps), meta=meta_from_request(request))


@router.get("/curated", response_model=Envelope[list[SkillRead]])
async def list_curated_skills(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[list[SkillRead]]:
    """Public — every skill with curated `/skills/[slug]` content (`seo_summary` set), for the
    sitemap generator (docs/SEO.md §2.3). Most skills in the taxonomy (resume-extracted/
    manually-added) have no curated content and still resolve at `/skills/{slug}`, they're just
    not submitted to search engines as thin pages."""
    result = await db.execute(
        select(Skill).where(Skill.seo_summary.is_not(None)).order_by(Skill.name)
    )
    rows = result.scalars().all()
    return Envelope(
        data=[SkillRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.get("/{id_or_slug}", response_model=Envelope[SkillDetailRead])
async def get_skill(
    request: Request,
    id_or_slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[SkillDetailRead]:
    """Public, unauthenticated — backs the indexable `/skills/[slug]` page (docs/SEO.md §1).
    No `published` gate: unlike `career_paths`, every skill in the taxonomy is a legitimate
    lookup target (resume-extracted/manually-added skills should resolve here too), just most
    have no curated `seo_summary` yet."""
    skill = await get_skill_by_id_or_slug(db, id_or_slug)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")

    related = await find_related_skills(db, skill)
    career_paths = await find_career_paths_requiring_skill(db, skill)
    data = SkillDetailRead.model_validate(skill)
    data.related_skills = [SkillRead.model_validate(r) for r in related]
    data.career_paths = [SkillCareerPathRef.model_validate(cp) for cp in career_paths]
    return Envelope(data=data, meta=meta_from_request(request))
