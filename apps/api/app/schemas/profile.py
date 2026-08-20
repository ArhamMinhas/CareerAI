import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.skill import Proficiency, SkillSource


def _check_date_order(start: date | None, end: date | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_date cannot be before start_date")


# --- Profile -----------------------------------------------------------------------------


class ProfileUpdate(BaseModel):
    """All fields optional — the router applies only what's actually present in the
    request body (`model_dump(exclude_unset=True)`), so a PATCH can clear a field by
    sending it as `null` without touching fields the client didn't mention."""

    full_name: str | None = Field(default=None, max_length=255)
    headline: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=1024)
    bio: str | None = None


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    headline: str | None
    location: str | None
    avatar_url: str | None
    bio: str | None


# --- Education -----------------------------------------------------------------------------


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _validate_dates(self) -> "EducationCreate":
        _check_date_order(self.start_date, self.end_date)
        return self


class EducationUpdate(BaseModel):
    institution: str | None = Field(default=None, min_length=1, max_length=255)
    degree: str | None = Field(default=None, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class EducationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution: str
    degree: str | None
    field_of_study: str | None
    start_date: date | None
    end_date: date | None
    description: str | None


# --- Experience ----------------------------------------------------------------------------


class ExperienceCreate(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=64)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _validate_dates(self) -> "ExperienceCreate":
        _check_date_order(self.start_date, self.end_date)
        return self


class ExperienceUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    employment_type: str | None = Field(default=None, max_length=64)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class ExperienceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company: str
    title: str
    location: str | None
    employment_type: str | None
    start_date: date | None
    end_date: date | None
    description: str | None


# --- Projects --------------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    url: str | None = Field(default=None, max_length=1024)
    repo_url: str | None = Field(default=None, max_length=1024)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _validate_dates(self) -> "ProjectCreate":
        _check_date_order(self.start_date, self.end_date)
        return self


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    url: str | None = Field(default=None, max_length=1024)
    repo_url: str | None = Field(default=None, max_length=1024)
    start_date: date | None = None
    end_date: date | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    url: str | None
    repo_url: str | None
    start_date: date | None
    end_date: date | None


# --- Skills (manual entry against the taxonomy) -----------------------------------------------


class UserSkillCreate(BaseModel):
    """`skill_name` rather than `skill_id` — Phase 3 is manual entry with autocomplete, so
    the router resolves (or creates) the taxonomy row by name; the client never needs to
    know a skill's id up front."""

    skill_name: str = Field(min_length=1, max_length=255)
    proficiency: Proficiency = Proficiency.INTERMEDIATE


class UserSkillUpdate(BaseModel):
    proficiency: Proficiency


class UserSkillRead(BaseModel):
    id: uuid.UUID
    skill_id: uuid.UUID
    name: str
    category: str | None
    proficiency: Proficiency
    source: SkillSource
