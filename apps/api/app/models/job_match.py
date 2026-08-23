import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.job import Job
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class JobMatch(UUIDPKMixin, TimestampMixin, Base):
    """A user's computed hybrid match score against one job — docs/DATABASE.md §2.3,
    docs/ML_PIPELINE.md §2.2. Cached/recomputed the same way as `SkillGap`
    (app/models/skill_gap.py): `POST /jobs/match` replaces this user's rows with a fresh
    computation rather than appending duplicates. Hard-deleted, not soft — cached computed
    output, not durable user content, same category as `SkillGap`/`UserSkill`."""

    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_job_matches_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSONB(), nullable=False)
    explanation: Mapped[str] = mapped_column(String(1024), nullable=False)

    job: Mapped["Job"] = relationship(lazy="selectin")


class ApplicationStatus(enum.StrEnum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"


class Application(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A user's tracked application to a job — docs/DATABASE.md §2.3. Soft-deleted: docs/
    DATABASE.md §1 names `applications` directly as one of the user-facing content tables that
    gets a `deleted_at` recovery path, unlike the cached/computed rows (`SkillGap`, `JobMatch`)
    this model sits next to.

    The uniqueness constraint is a **partial** unique index over non-deleted rows rather than a
    plain `UniqueConstraint`, specifically because of the soft-delete: a user who removes
    (soft-deletes) a tracked application and later wants to track that same job again must be
    able to insert a fresh row — a plain unique constraint would still see the old, soft-deleted
    row and reject the re-insert with a spurious conflict.
    """

    __tablename__ = "applications"
    __table_args__ = (
        Index(
            "uq_applications_user_job_active",
            "user_id",
            "job_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.SAVED,
        nullable=False,
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["Job"] = relationship(lazy="selectin")
