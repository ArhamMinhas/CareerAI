import uuid

from pydantic import BaseModel, ConfigDict, Field


class CareerGoalCreate(BaseModel):
    target_role: str = Field(min_length=1, max_length=255)
    target_industry: str | None = Field(default=None, max_length=255)
    target_years_experience: int | None = Field(default=None, ge=0, le=60)
    is_active: bool = True


class CareerGoalUpdate(BaseModel):
    target_role: str | None = Field(default=None, min_length=1, max_length=255)
    target_industry: str | None = Field(default=None, max_length=255)
    target_years_experience: int | None = Field(default=None, ge=0, le=60)
    is_active: bool | None = None


class CareerGoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_role: str
    target_industry: str | None
    target_years_experience: int | None
    is_active: bool
