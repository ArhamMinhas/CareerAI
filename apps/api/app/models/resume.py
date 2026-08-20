import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class FileType(enum.StrEnum):
    PDF = "PDF"
    DOCX = "DOCX"


class ResumeStatus(enum.StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Resume(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """docs/DATABASE.md §2.2. `structured_data` is the full extraction result (contact info,
    skills, experience, education, projects — see app/schemas/resume.py `ResumeExtraction`);
    `score_breakdown` is the per-sub-score `{score, explanation, evidence}` map behind
    `overall_score`, per docs/ML_PIPELINE.md §2.1's explainability requirement."""

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, name="resume_file_type"), nullable=False
    )
    status: Mapped[ResumeStatus] = mapped_column(
        Enum(ResumeStatus, name="resume_status"), default=ResumeStatus.UPLOADED, nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)


class ResumeVersion(UUIDPKMixin, TimestampMixin, Base):
    """A snapshot taken each time a resume is (re-)analyzed — docs/API.md
    `POST /resumes/{id}/analyze` — so scoring history isn't lost when a re-score changes the
    live `resumes` row."""

    __tablename__ = "resume_versions"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    structured_data: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
