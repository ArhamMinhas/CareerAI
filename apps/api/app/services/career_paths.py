from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_path import CareerPath
from app.models.skill import slugify


class CareerPathNotFoundError(Exception):
    pass


async def resolve_career_path(db: AsyncSession, target_role: str) -> CareerPath:
    """Resolves a free-text target role (e.g. `career_goals.target_role`, or a
    `?target_role=` query param) to a published `CareerPath` — first by exact match on the
    slugified input, then an exact case-insensitive title match, since callers type roles as
    prose ("AI Engineer") while the catalog keys on a URL-safe slug ("ai-engineer"). The title
    match is a plain case-folded equality, not `ILIKE` — `target_role` is arbitrary caller
    input, and `ILIKE` treats `%`/`_` in it as wildcards, which could match zero, one, or *more
    than one* row (a bare `%` matches every published path) and crash `scalar_one_or_none()`
    with `MultipleResultsFound` instead of cleanly resolving to "not found"."""
    slug = slugify(target_role)
    result = await db.execute(
        select(CareerPath).where(CareerPath.slug == slug, CareerPath.published.is_(True))
    )
    career_path = result.scalar_one_or_none()
    if career_path is not None:
        return career_path

    result = await db.execute(
        select(CareerPath).where(
            func.lower(CareerPath.title) == target_role.strip().lower(),
            CareerPath.published.is_(True),
        )
    )
    career_path = result.scalar_one_or_none()
    if career_path is None:
        raise CareerPathNotFoundError(f"No curated career path matches '{target_role}' yet.")
    return career_path


async def list_career_paths(db: AsyncSession) -> list[CareerPath]:
    result = await db.execute(
        select(CareerPath).where(CareerPath.published.is_(True)).order_by(CareerPath.title)
    )
    return list(result.scalars().all())


async def get_career_path_by_slug(db: AsyncSession, slug: str) -> CareerPath | None:
    result = await db.execute(
        select(CareerPath).where(CareerPath.slug == slug, CareerPath.published.is_(True))
    )
    return result.scalar_one_or_none()


async def find_related_career_paths(
    db: AsyncSession, career_path: CareerPath, *, limit: int = 3
) -> list[CareerPath]:
    """Nearest neighbors by `embedding` cosine distance (pgvector `<=>`), excluding itself.
    Returns an empty list when this career path has no embedding yet — a missing "related
    paths" section degrades gracefully rather than erroring."""
    if career_path.embedding is None:
        return []
    result = await db.execute(
        select(CareerPath)
        .where(
            CareerPath.published.is_(True),
            CareerPath.id != career_path.id,
            CareerPath.embedding.is_not(None),
        )
        .order_by(CareerPath.embedding.cosine_distance(career_path.embedding))
        .limit(limit)
    )
    return list(result.scalars().all())
