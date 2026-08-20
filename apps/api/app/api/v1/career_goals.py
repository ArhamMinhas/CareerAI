import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.career_goal import CareerGoal
from app.models.user import User
from app.schemas.career_goal import CareerGoalCreate, CareerGoalRead, CareerGoalUpdate
from app.schemas.envelope import Envelope, meta_from_request

router = APIRouter(prefix="/career-goals", tags=["career-goals"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=Envelope[list[CareerGoalRead]])
async def list_career_goals(
    request: Request, user: UserDep, db: DbDep
) -> Envelope[list[CareerGoalRead]]:
    result = await db.execute(
        select(CareerGoal)
        .where(CareerGoal.user_id == user.id)
        .order_by(CareerGoal.created_at.desc())
    )
    rows = result.scalars().all()
    return Envelope(
        data=[CareerGoalRead.model_validate(r) for r in rows], meta=meta_from_request(request)
    )


@router.post("", response_model=Envelope[CareerGoalRead], status_code=status.HTTP_201_CREATED)
async def create_career_goal(
    request: Request, body: CareerGoalCreate, user: UserDep, db: DbDep
) -> Envelope[CareerGoalRead]:
    row = CareerGoal(user_id=user.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return Envelope(data=CareerGoalRead.model_validate(row), meta=meta_from_request(request))


@router.patch("/{career_goal_id}", response_model=Envelope[CareerGoalRead])
async def update_career_goal(
    request: Request,
    career_goal_id: uuid.UUID,
    body: CareerGoalUpdate,
    user: UserDep,
    db: DbDep,
) -> Envelope[CareerGoalRead]:
    result = await db.execute(
        select(CareerGoal).where(CareerGoal.id == career_goal_id, CareerGoal.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return Envelope(data=CareerGoalRead.model_validate(row), meta=meta_from_request(request))


@router.delete("/{career_goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_career_goal(career_goal_id: uuid.UUID, user: UserDep, db: DbDep) -> None:
    result = await db.execute(
        select(CareerGoal).where(CareerGoal.id == career_goal_id, CareerGoal.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    await db.delete(row)
    await db.commit()
