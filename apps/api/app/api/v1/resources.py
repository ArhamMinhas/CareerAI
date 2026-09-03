from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.resource import ResourceDetailRead, ResourceRead
from app.services.resources import find_related_resources, get_resource_by_slug, list_resources

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=Envelope[list[ResourceRead]])
async def get_resources(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[list[ResourceRead]]:
    """Public, unauthenticated — backs the indexable `/resources` index page and `sitemap.ts`
    (docs/SEO.md §1). Not paginated: the curated catalog is small by design, not an unbounded
    feed — same reasoning as `GET /careers`."""
    resources = await list_resources(db)
    return Envelope(
        data=[ResourceRead.model_validate(r) for r in resources],
        meta=meta_from_request(request),
    )


@router.get("/{slug}", response_model=Envelope[ResourceDetailRead])
async def get_resource(
    request: Request,
    slug: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Envelope[ResourceDetailRead]:
    """Public, unauthenticated — backs the indexable `/resources/[slug]` page. This is the same
    curated content the RAG pipeline (`app/ai/rag_answer.py`) chunks and retrieves against, per
    docs/ROADMAP.md's Phase 9 dual-purpose content pattern."""
    resource = await get_resource_by_slug(db, slug)
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")

    related = await find_related_resources(db, resource)
    data = ResourceDetailRead.model_validate(resource)
    data.related_resources = [ResourceRead.model_validate(r) for r in related]

    return Envelope(data=data, meta=meta_from_request(request))
