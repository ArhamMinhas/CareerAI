import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.pagination import InvalidCursorError
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.job import JobDetailRead, JobRead
from app.schemas.job_match import JobFitRead, JobMatchRead
from app.services.job_matching import compute_job_fit, refresh_job_matches
from app.services.jobs import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    get_active_job,
    list_jobs,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Envelope[list[JobRead]])
async def get_jobs(
    request: Request,
    db: DbDep,
    q: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    cursor: str | None = Query(default=None),
) -> Envelope[list[JobRead]]:
    """Public, unauthenticated — backs the indexable `/jobs` listing. `q` does a keyword-then-
    semantic search (see `app.services.jobs.list_jobs`); the semantic fallback path returns an
    unpaginated single page, so `next_cursor` is only ever set when the keyword path (or the
    unfiltered listing) produced the page."""
    try:
        jobs, next_cursor = await list_jobs(db, q=q, limit=limit, cursor=cursor)
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Envelope(
        data=[JobRead.model_validate(job) for job in jobs],
        meta=meta_from_request(request, next_cursor=next_cursor),
    )


@router.post("/match", response_model=Envelope[list[JobMatchRead]])
async def post_job_match(
    request: Request, user: UserDep, db: DbDep
) -> Envelope[list[JobMatchRead]]:
    """Recomputes this user's job matches against the current candidate pool
    (docs/ML_PIPELINE.md §2.2) — call after updating skills/resume/career goals so ranked
    matches reflect the current profile, mirroring `POST /skills/gaps/refresh`."""
    matches = await refresh_job_matches(db, user=user)
    await db.commit()
    return Envelope(
        data=[JobMatchRead.model_validate(m) for m in matches], meta=meta_from_request(request)
    )


@router.get("/{job_id}", response_model=Envelope[JobDetailRead])
async def get_job(request: Request, job_id: uuid.UUID, db: DbDep) -> Envelope[JobDetailRead]:
    """Public, unauthenticated — backs the indexable `/jobs/[id]` page. ID-routed, not
    slug-routed (see `Job`'s docstring and `Company`'s for the contrast)."""
    job = await get_active_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return Envelope(data=JobDetailRead.model_validate(job), meta=meta_from_request(request))


@router.get("/{job_id}/match", response_model=Envelope[JobFitRead])
async def get_job_fit(
    request: Request, job_id: uuid.UUID, user: UserDep, db: DbDep
) -> Envelope[JobFitRead]:
    """Authenticated — a live "how well do I fit this job" score for one specific posting, so
    the search/detail pages can show a fit percentage without requiring the user to have already
    run the batch `/matches` refresh (that pool is capped to `CANDIDATE_POOL_SIZE` nearest
    postings, which a job found via keyword search may fall outside of)."""
    job = await get_active_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    score, breakdown, explanation = await compute_job_fit(db, user=user, job=job)
    return Envelope(
        data=JobFitRead(match_score=score, score_breakdown=breakdown, explanation=explanation),
        meta=meta_from_request(request),
    )
