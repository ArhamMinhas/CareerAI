from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=Envelope[UserRead])
async def read_current_user(
    request: Request, user: Annotated[User, Depends(get_current_user)]
) -> Envelope[UserRead]:
    return Envelope(data=UserRead.model_validate(user), meta=meta_from_request(request))
