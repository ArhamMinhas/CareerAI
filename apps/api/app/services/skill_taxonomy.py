from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill import Skill, slugify


async def get_or_create_skill(db: AsyncSession, name: str) -> Skill:
    """Slug-deduped get-or-create against the shared skill taxonomy. Uses a SAVEPOINT (not a
    full commit/rollback) so this is safe to call from inside a larger transaction — e.g. the
    resume-processing task (app/workers/resume_tasks.py), which also updates the resume row
    and inserts a version snapshot in the same unit of work — as well as standalone (profile
    skill CRUD, app/api/v1/profile.py). A rollback here only undoes this savepoint, never
    whatever else the caller's transaction was doing.
    """
    clean_name = name.strip()
    slug = slugify(clean_name)

    result = await db.execute(select(Skill).where(Skill.slug == slug))
    skill = result.scalar_one_or_none()
    if skill is not None:
        return skill

    try:
        async with db.begin_nested():
            skill = Skill(name=clean_name, slug=slug)
            db.add(skill)
            await db.flush()
    except IntegrityError:
        # Another request/task created the same skill concurrently (unique slug/name).
        result = await db.execute(select(Skill).where(Skill.slug == slug))
        skill = result.scalar_one()
    return skill
