import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.job_match import Application
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationsResponse,
    ApplicationUpdate,
)
from app.schemas.envelope import Envelope, meta_from_request
from app.services.applications import get_owned_application, list_applications
from app.services.jobs import get_active_job

router = APIRouter(prefix="/applications", tags=["applications"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Envelope[ApplicationsResponse])
async def get_applications(
    request: Request, user: UserDep, db: DbDep
) -> Envelope[ApplicationsResponse]:
    """The applications tracker view. Not cursor-paginated (see `ApplicationsResponse`'s
    docstring): a single user's tracked applications are small enough to return in one page,
    unlike the site-wide `jobs` catalog."""
    applications = await list_applications(db, user_id=user.id)
    return Envelope(
        data=ApplicationsResponse(
            applications=[ApplicationRead.model_validate(a) for a in applications]
        ),
        meta=meta_from_request(request),
    )


@router.post("", response_model=Envelope[ApplicationRead], status_code=status.HTTP_201_CREATED)
async def create_application(
    request: Request, body: ApplicationCreate, user: UserDep, db: DbDep
) -> Envelope[ApplicationRead]:
    job = await get_active_job(db, body.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    application = Application(user_id=user.id, **body.model_dump())
    db.add(application)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You're already tracking an application for this job.",
        ) from exc
    await db.refresh(application)
    application.job = job
    return Envelope(
        data=ApplicationRead.model_validate(application), meta=meta_from_request(request)
    )


@router.patch("/{application_id}", response_model=Envelope[ApplicationRead])
async def update_application(
    request: Request,
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    user: UserDep,
    db: DbDep,
) -> Envelope[ApplicationRead]:
    application = await get_owned_application(db, application_id=application_id, user_id=user.id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    await db.commit()
    await db.refresh(application)
    return Envelope(
        data=ApplicationRead.model_validate(application), meta=meta_from_request(request)
    )


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(application_id: uuid.UUID, user: UserDep, db: DbDep) -> None:
    application = await get_owned_application(db, application_id=application_id, user_id=user.id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    application.soft_delete()
    await db.commit()
