from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Company(UUIDPKMixin, TimestampMixin, Base):
    """A hiring organization — docs/DATABASE.md §2.3. Hard-deleted, not soft: reference/lookup
    content, same category as `Skill`/`Job` (docs/DATABASE.md §1).

    Routed by `slug` (`/companies/{slug}`), not the `[id]` docs/ROADMAP.md's Phase 7 entry
    literally says — the ERD already gave this table a unique `slug` (unlike `Job`, which has
    none), and every other public content type in this app (career paths, skills) is
    slug-routed for the same reason: stable, readable, better for SEO than an opaque UUID. A
    company's name doesn't churn the way a job posting does, so it earns the same treatment.
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
