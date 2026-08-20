import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.resume import FileType, ResumeStatus

# --- Extraction (NLP + LLM structured output, stored as `resumes.structured_data`) -----------


class ExtractedExperience(BaseModel):
    company: str = ""
    title: str = ""
    start_date: str | None = None
    end_date: str | None = None
    description: str = ""
    bullets: list[str] = Field(default_factory=list)


class ExtractedEducation(BaseModel):
    institution: str = ""
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ExtractedProject(BaseModel):
    title: str = ""
    description: str = ""
    url: str | None = None


class ResumeExtraction(BaseModel):
    """The LLM's structured read of the resume — passed as `response_format` to the OpenAI
    call (app/ai/resume_extraction.py) and re-validated against this schema before use, per
    docs/AI_ARCHITECTURE.md §3. Every field defaults so a partial/unclear resume still
    produces a valid object rather than a validation failure."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ExtractedExperience] = Field(default_factory=list)
    education: list[ExtractedEducation] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


# --- Scoring (docs/ML_PIPELINE.md §2.1) -------------------------------------------------------


class SubScore(BaseModel):
    """Every sub-score is explainable — spec §14 — never a bare number."""

    score: float = Field(ge=0, le=100)
    explanation: str
    evidence: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    ats_compatibility: SubScore
    skills: SubScore
    experience: SubScore
    projects: SubScore
    education: SubScore
    achievements: SubScore
    keywords: SubScore
    structure: SubScore


# --- API request/response ----------------------------------------------------------------------


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    file_type: FileType
    status: ResumeStatus
    overall_score: float | None
    failure_reason: str | None
    created_at: datetime


class ResumeDetailRead(ResumeRead):
    structured_data: ResumeExtraction | None
    score_breakdown: ScoreBreakdown | None
    file_download_url: str | None = None


class ResumeStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ResumeStatus
    failure_reason: str | None


class ResumeVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    overall_score: float | None
    score_breakdown: ScoreBreakdown | None
    created_at: datetime
