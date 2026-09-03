from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource import Resource


async def list_resources(db: AsyncSession) -> list[Resource]:
    result = await db.execute(
        select(Resource).where(Resource.published.is_(True)).order_by(Resource.title)
    )
    return list(result.scalars().all())


async def get_resource_by_slug(db: AsyncSession, slug: str) -> Resource | None:
    result = await db.execute(
        select(Resource).where(Resource.slug == slug, Resource.published.is_(True))
    )
    return result.scalar_one_or_none()


async def find_related_resources(
    db: AsyncSession, resource: Resource, *, limit: int = 3
) -> list[Resource]:
    """Nearest neighbors by whole-document `embedding` cosine distance (pgvector `<=>`),
    excluding itself — same pattern as `find_related_career_paths`. Returns an empty list when
    this resource has no embedding yet, degrading gracefully rather than erroring."""
    if resource.embedding is None:
        return []
    result = await db.execute(
        select(Resource)
        .where(
            Resource.published.is_(True),
            Resource.id != resource.id,
            Resource.embedding.is_not(None),
        )
        .order_by(Resource.embedding.cosine_distance(resource.embedding))
        .limit(limit)
    )
    return list(result.scalars().all())
