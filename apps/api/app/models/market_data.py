import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin
from app.models.skill import Skill


class SkillDemand(UUIDPKMixin, TimestampMixin, Base):
    """Real, aggregated weekly skill-demand counts — docs/DATABASE.md §2.5,
    docs/ML_PIPELINE.md §3 model 6 (Phase 8). Populated by
    `app/scripts/aggregate_market_data.py` from real `job_skills`/`jobs.posted_at` data, not
    fabricated. No `region` column (unlike the original ERD) — every job currently ingested is
    US-only, and adding a region dimension would fragment an already-thin ~400-job base into
    near-empty cells; revisit once postings span multiple real regions.

    `growth_rate` is left `NULL`, not computed, when the prior period's `demand_count` for this
    skill is below `app/services/market_data.MIN_PERIOD_COUNT` — a growth rate computed from a
    near-zero denominator is noise, not signal, and both `_priority()`
    (app/services/skill_gap.py) and the model 6 forecast explicitly skip blending a `NULL` rather
    than treating it as zero growth.

    Hard-deleted, fully replaced per period on every aggregation run — cached computed output,
    same category as `SkillGap`/`JobMatch`, not durable user content."""

    __tablename__ = "skill_demand"
    __table_args__ = (UniqueConstraint("skill_id", "period", name="uq_skill_demand_skill_period"),)

    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    demand_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    growth_rate: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    period: Mapped[date] = mapped_column(Date(), nullable=False, index=True)

    skill: Mapped["Skill"] = relationship(lazy="selectin")


class SalaryData(UUIDPKMixin, TimestampMixin, Base):
    """Real, aggregated weekly salary percentiles by (job_title, seniority_level) —
    docs/DATABASE.md §2.5, docs/ML_PIPELINE.md §3 model 4's baseline ("median salary by (title,
    region) lookup"). Populated by `app/scripts/aggregate_market_data.py` from real
    `jobs.salary_min`/`salary_max`. No `region` column, same reasoning as `SkillDemand` — every
    job currently ingested is US-only.

    `job_title` is the raw posting title, not a normalized category — model 5's
    `Job.predicted_category` is a separate, coarser signal; this table stays title-grained since
    that's what the baseline lookup and the regression model's features both need. Hard-deleted,
    fully replaced per period on every aggregation run, same category as `SkillDemand`."""

    __tablename__ = "salary_data"
    __table_args__ = (
        UniqueConstraint(
            "job_title", "seniority_level", "period", name="uq_salary_data_title_seniority_period"
        ),
    )

    job_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    seniority_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    p25: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    p50: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    p75: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    period: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
