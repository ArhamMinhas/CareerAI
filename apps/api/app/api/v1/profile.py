import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.education import Education
from app.models.experience import Experience
from app.models.profile import Profile
from app.models.project import Project
from app.models.skill import UserSkill
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.profile import (
    EducationCreate,
    EducationRead,
    EducationUpdate,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    ProfileRead,
    ProfileUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    UserSkillCreate,
    UserSkillRead,
    UserSkillUpdate,
)
from app.services.skill_taxonomy import get_or_create_skill

router = APIRouter(prefix="/profile", tags=["profile"])


async def _get_or_create_profile(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Profile:
    """A `User` doesn't get a `Profile` row at signup (docs/DATABASE.md §2.1 keeps them as
    separate one-to-one tables) — lazily created on first touch, same pattern
    `get_current_user` already uses for the `users` row itself (app/core/security.py)."""
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


ProfileDep = Annotated[Profile, Depends(_get_or_create_profile)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _get_owned(model: Any, row_id: uuid.UUID, profile: Profile, db: AsyncSession) -> Any:
    """Fetches a child row by id, scoped to the caller's own profile — a 404 (never 403)
    for a row that exists but belongs to someone else, so ownership isn't leaked. Typed
    `Any` rather than a generic: every call site immediately narrows via its own
    `response_model`/attribute access, and a real generic bound (`profile_id` isn't on a
    shared protocol any of these models implement) would add more type-only ceremony than
    the four call sites are worth."""
    result = await db.execute(
        select(model).where(model.id == row_id, model.profile_id == profile.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return row


# --- Profile -------------------------------------------------------------------------------


@router.get("", response_model=Envelope[ProfileRead])
async def read_profile(request: Request, profile: ProfileDep) -> Envelope[ProfileRead]:
    return Envelope(data=ProfileRead.model_validate(profile), meta=meta_from_request(request))


@router.patch("", response_model=Envelope[ProfileRead])
async def update_profile(
    request: Request, body: ProfileUpdate, profile: ProfileDep, db: DbDep
) -> Envelope[ProfileRead]:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return Envelope(data=ProfileRead.model_validate(profile), meta=meta_from_request(request))


# --- Education -------------------------------------------------------------------------------


@router.get("/education", response_model=Envelope[list[EducationRead]])
async def list_education(
    request: Request, profile: ProfileDep, db: DbDep
) -> Envelope[list[EducationRead]]:
    result = await db.execute(
        select(Education)
        .where(Education.profile_id == profile.id, Education.deleted_at.is_(None))
        .order_by(Education.start_date.desc().nullslast())
    )
    rows = result.scalars().all()
    return Envelope(
        data=[EducationRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.post(
    "/education", response_model=Envelope[EducationRead], status_code=status.HTTP_201_CREATED
)
async def create_education(
    request: Request, body: EducationCreate, profile: ProfileDep, db: DbDep
) -> Envelope[EducationRead]:
    row = Education(profile_id=profile.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return Envelope(data=EducationRead.model_validate(row), meta=meta_from_request(request))


@router.patch("/education/{education_id}", response_model=Envelope[EducationRead])
async def update_education(
    request: Request, education_id: uuid.UUID, body: EducationUpdate, profile: ProfileDep, db: DbDep
) -> Envelope[EducationRead]:
    row = await _get_owned(Education, education_id, profile, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    if row.start_date is not None and row.end_date is not None and row.end_date < row.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_date cannot be before start_date",
        )
    await db.commit()
    await db.refresh(row)
    return Envelope(data=EducationRead.model_validate(row), meta=meta_from_request(request))


@router.delete("/education/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_education(education_id: uuid.UUID, profile: ProfileDep, db: DbDep) -> None:
    row = await _get_owned(Education, education_id, profile, db)
    row.soft_delete()
    await db.commit()


# --- Experience ------------------------------------------------------------------------------


@router.get("/experience", response_model=Envelope[list[ExperienceRead]])
async def list_experience(
    request: Request, profile: ProfileDep, db: DbDep
) -> Envelope[list[ExperienceRead]]:
    result = await db.execute(
        select(Experience)
        .where(Experience.profile_id == profile.id, Experience.deleted_at.is_(None))
        .order_by(Experience.start_date.desc().nullslast())
    )
    rows = result.scalars().all()
    return Envelope(
        data=[ExperienceRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.post(
    "/experience", response_model=Envelope[ExperienceRead], status_code=status.HTTP_201_CREATED
)
async def create_experience(
    request: Request, body: ExperienceCreate, profile: ProfileDep, db: DbDep
) -> Envelope[ExperienceRead]:
    row = Experience(profile_id=profile.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return Envelope(data=ExperienceRead.model_validate(row), meta=meta_from_request(request))


@router.patch("/experience/{experience_id}", response_model=Envelope[ExperienceRead])
async def update_experience(
    request: Request,
    experience_id: uuid.UUID,
    body: ExperienceUpdate,
    profile: ProfileDep,
    db: DbDep,
) -> Envelope[ExperienceRead]:
    row = await _get_owned(Experience, experience_id, profile, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    if row.start_date is not None and row.end_date is not None and row.end_date < row.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_date cannot be before start_date",
        )
    await db.commit()
    await db.refresh(row)
    return Envelope(data=ExperienceRead.model_validate(row), meta=meta_from_request(request))


@router.delete("/experience/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(experience_id: uuid.UUID, profile: ProfileDep, db: DbDep) -> None:
    row = await _get_owned(Experience, experience_id, profile, db)
    row.soft_delete()
    await db.commit()


# --- Projects --------------------------------------------------------------------------------


@router.get("/projects", response_model=Envelope[list[ProjectRead]])
async def list_projects(
    request: Request, profile: ProfileDep, db: DbDep
) -> Envelope[list[ProjectRead]]:
    result = await db.execute(
        select(Project)
        .where(Project.profile_id == profile.id, Project.deleted_at.is_(None))
        .order_by(Project.start_date.desc().nullslast())
    )
    rows = result.scalars().all()
    return Envelope(
        data=[ProjectRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.post("/projects", response_model=Envelope[ProjectRead], status_code=status.HTTP_201_CREATED)
async def create_project(
    request: Request, body: ProjectCreate, profile: ProfileDep, db: DbDep
) -> Envelope[ProjectRead]:
    row = Project(profile_id=profile.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return Envelope(data=ProjectRead.model_validate(row), meta=meta_from_request(request))


@router.patch("/projects/{project_id}", response_model=Envelope[ProjectRead])
async def update_project(
    request: Request, project_id: uuid.UUID, body: ProjectUpdate, profile: ProfileDep, db: DbDep
) -> Envelope[ProjectRead]:
    row = await _get_owned(Project, project_id, profile, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    if row.start_date is not None and row.end_date is not None and row.end_date < row.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_date cannot be before start_date",
        )
    await db.commit()
    await db.refresh(row)
    return Envelope(data=ProjectRead.model_validate(row), meta=meta_from_request(request))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: uuid.UUID, profile: ProfileDep, db: DbDep) -> None:
    row = await _get_owned(Project, project_id, profile, db)
    row.soft_delete()
    await db.commit()


# --- Skills (manual entry) --------------------------------------------------------------------


def _user_skill_read(row: UserSkill) -> UserSkillRead:
    return UserSkillRead(
        id=row.id,
        skill_id=row.skill_id,
        name=row.skill.name,
        category=row.skill.category,
        proficiency=row.proficiency,
        source=row.source,
    )


@router.get("/skills", response_model=Envelope[list[UserSkillRead]])
async def list_user_skills(
    request: Request, profile: ProfileDep, db: DbDep
) -> Envelope[list[UserSkillRead]]:
    result = await db.execute(select(UserSkill).where(UserSkill.profile_id == profile.id))
    rows = result.scalars().all()
    return Envelope(data=[_user_skill_read(r) for r in rows], meta=meta_from_request(request))


@router.post("/skills", response_model=Envelope[UserSkillRead], status_code=status.HTTP_201_CREATED)
async def create_user_skill(
    request: Request, body: UserSkillCreate, profile: ProfileDep, db: DbDep
) -> Envelope[UserSkillRead]:
    skill = await get_or_create_skill(db, body.skill_name)

    existing = await db.execute(
        select(UserSkill).where(UserSkill.profile_id == profile.id, UserSkill.skill_id == skill.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This skill is already on your profile."
        )

    row = UserSkill(profile_id=profile.id, skill_id=skill.id, proficiency=body.proficiency)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return Envelope(data=_user_skill_read(row), meta=meta_from_request(request))


@router.patch("/skills/{user_skill_id}", response_model=Envelope[UserSkillRead])
async def update_user_skill(
    request: Request,
    user_skill_id: uuid.UUID,
    body: UserSkillUpdate,
    profile: ProfileDep,
    db: DbDep,
) -> Envelope[UserSkillRead]:
    row = await _get_owned(UserSkill, user_skill_id, profile, db)
    row.proficiency = body.proficiency
    await db.commit()
    await db.refresh(row)
    return Envelope(data=_user_skill_read(row), meta=meta_from_request(request))


@router.delete("/skills/{user_skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_skill(user_skill_id: uuid.UUID, profile: ProfileDep, db: DbDep) -> None:
    row = await _get_owned(UserSkill, user_skill_id, profile, db)
    await db.delete(row)
    await db.commit()
