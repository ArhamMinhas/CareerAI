import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.company import Company
from app.models.mixins import TimestampMixin, UUIDPKMixin
from app.models.skill import SKILL_EMBEDDING_DIMENSIONS, Skill


class Job(UUIDPKMixin, TimestampMixin, Base):
    """A job posting — docs/DATABASE.md §2.3. Hard-deleted, not soft (§1) — reference/lookup
    content, same category as `Skill`/`Company`.

    `is_active` isn't in the original ERD but is needed for exactly what docs/SEO.md §2.4
    describes for `JobPosting.validThrough`: "derived from job status so expired postings stop
    appearing as active listings." Same precedent as `Skill.synonyms`/`seo_summary`/`embedding`
    — a column the ERD's own prose anticipated, added when the phase that needs it arrives.

    `source`/`external_id`/`apply_url` back real job ingestion (app/services/adzuna_ingestion.py)
    alongside the hand-written demo postings from `app/scripts/seed_jobs.py` (`source=None` for
    those). `(source, external_id)` is uniquely constrained so re-ingesting the same upstream
    posting updates it in place instead of duplicating it — nullable, so the many `source=None`
    demo rows don't collide with each other under Postgres's NULLs-are-distinct semantics.
    `apply_url` is the real external application link a job board API provides; without one
    (demo postings), the frontend simply doesn't render an "Apply" button.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        Index(
            "ix_jobs_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    seniority_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote: Mapped[bool] = mapped_column(Boolean(), default=False, nullable=False)
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(SKILL_EMBEDDING_DIMENSIONS), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apply_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    company: Mapped["Company"] = relationship(lazy="selectin")
    required_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job",
        lazy="selectin",
        order_by="JobSkill.weight.desc()",
        cascade="all, delete-orphan",
    )


class JobSkill(UUIDPKMixin, Base):
    """A skill this job posting names — docs/DATABASE.md §2.3. Mirrors `CareerPathSkill`'s
    shape (weight + a flag), but `is_required` rather than `is_core`: a job's skill list
    genuinely distinguishes "required" from "nice to have," where a career path's `is_core`
    is about how central a skill is to the *role* in general."""

    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("job_id", "skill_id", name="uq_job_skills_job_skill"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_required: Mapped[bool] = mapped_column(Boolean(), default=True, nullable=False)
    weight: Mapped[int] = mapped_column(Integer(), default=5, nullable=False)

    job: Mapped["Job"] = relationship(back_populates="required_skills")
    skill: Mapped["Skill"] = relationship(lazy="selectin")
