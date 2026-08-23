import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job_match import ApplicationStatus
from app.schemas.job import JobRead


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    status: ApplicationStatus = ApplicationStatus.SAVED
    applied_at: datetime | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    applied_at: datetime | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job: JobRead
    status: ApplicationStatus
    applied_at: datetime | None
    created_at: datetime


class ApplicationsResponse(BaseModel):
    """`GET /api/v1/applications` — a flat tracker list is small enough per user (no jobs-scale
    pagination need, unlike `/jobs`), so this returns everything rather than a cursor page."""

    applications: list[ApplicationRead] = Field(default_factory=list)
