import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_path import CareerPath, CareerPathSkill
from app.models.skill import Skill


async def get_skill_by_id_or_slug(db: AsyncSession, id_or_slug: str) -> Skill | None:
    """`/api/v1/skills/{id_or_slug}` accepts either so the public `/skills/[slug]` page can
    link by slug while internal callers that already hold a UUID don't need a second lookup."""
    try:
        skill_id = uuid.UUID(id_or_slug)
    except ValueError:
        skill_id = None

    if skill_id is not None:
        return await db.get(Skill, skill_id)

    result = await db.execute(select(Skill).where(Skill.slug == id_or_slug))
    return result.scalar_one_or_none()


async def find_related_skills(db: AsyncSession, skill: Skill, *, limit: int = 6) -> list[Skill]:
    """Nearest neighbors by `embedding` cosine distance (pgvector `<=>`), excluding itself.
    Returns an empty list when this skill has no embedding yet (most skills — see
    `app.models.skill.Skill`'s docstring) rather than erroring."""
    if skill.embedding is None:
        return []
    result = await db.execute(
        select(Skill)
        .where(Skill.id != skill.id, Skill.embedding.is_not(None))
        .order_by(Skill.embedding.cosine_distance(skill.embedding))
        .limit(limit)
    )
    return list(result.scalars().all())


async def find_career_paths_requiring_skill(db: AsyncSession, skill: Skill) -> list[CareerPath]:
    """Cross-links a skill page back to the career paths that require it (docs/API.md §5) — a
    real internal-linking win for SEO and genuinely useful navigation, not just decoration."""
    result = await db.execute(
        select(CareerPath)
        .join(CareerPathSkill, CareerPathSkill.career_path_id == CareerPath.id)
        .where(CareerPathSkill.skill_id == skill.id, CareerPath.published.is_(True))
        .order_by(CareerPath.title)
    )
    return list(result.scalars().all())
