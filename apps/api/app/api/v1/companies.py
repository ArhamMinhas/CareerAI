from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.pagination import InvalidCursorError
from app.models.company import Company
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.job import CompanyDetailRead, JobRead
from app.services.jobs import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, list_active_jobs_for_company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/{slug}", response_model=Envelope[CompanyDetailRead])
async def get_company(
    request: Request,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[CompanyDetailRead]:
    """Public, unauthenticated — backs the indexable `/companies/[slug]` page. `jobs` is this
    company's currently-active postings, capped to one page (`DEFAULT_PAGE_SIZE`) — a company
    detail page links out to `/companies/{slug}/jobs` for the full paginated list rather than
    inlining every posting here."""
    result = await db.execute(select(Company).where(Company.slug == slug))
    company = result.scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    jobs, _ = await list_active_jobs_for_company(
        db, company.id, limit=DEFAULT_PAGE_SIZE, cursor=None
    )
    data = CompanyDetailRead.model_validate(company)
    data.jobs = [JobRead.model_validate(job) for job in jobs]
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("/{slug}/jobs", response_model=Envelope[list[JobRead]])
async def get_company_jobs(
    request: Request,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    cursor: str | None = Query(default=None),
) -> Envelope[list[JobRead]]:
    """The paginated counterpart to the `jobs` slice embedded in `GET /companies/{slug}` —
    docs/API.md §1's cursor convention (`next_cursor` in `meta`)."""
    result = await db.execute(select(Company.id).where(Company.slug == slug))
    company_id = result.scalar_one_or_none()
    if company_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    try:
        jobs, next_cursor = await list_active_jobs_for_company(
            db, company_id, limit=limit, cursor=cursor
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Envelope(
        data=[JobRead.model_validate(job) for job in jobs],
        meta=meta_from_request(request, next_cursor=next_cursor),
    )
