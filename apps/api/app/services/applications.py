import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_match import Application


async def list_applications(db: AsyncSession, *, user_id: uuid.UUID) -> list[Application]:
    result = await db.execute(
        select(Application)
        .where(Application.user_id == user_id, Application.deleted_at.is_(None))
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())


async def get_owned_application(
    db: AsyncSession, *, application_id: uuid.UUID, user_id: uuid.UUID
) -> Application | None:
    result = await db.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
            Application.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()
