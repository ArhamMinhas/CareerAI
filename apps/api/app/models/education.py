import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class Education(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    """One entry in a profile's education history — docs/DATABASE.md §2.1/§2.2.

    `end_date` left null means "currently enrolled" — no separate boolean, so there's
    nothing to fall out of sync with the dates themselves. No `profile` relationship: the
    router always already has `profile_id` in hand and queries this table directly (see
    `app/models/profile.py` for why).
    """

    __tablename__ = "education"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
