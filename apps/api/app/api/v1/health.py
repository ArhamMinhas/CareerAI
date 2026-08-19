from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.schemas.envelope import Envelope, meta_from_request

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: str


@router.get("/health", response_model=Envelope[HealthStatus])
async def health_check(request: Request) -> Envelope[HealthStatus]:
    return Envelope(data=HealthStatus(status="ok"), meta=meta_from_request(request))
