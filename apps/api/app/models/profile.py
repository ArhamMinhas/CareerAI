import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.user import User


class Profile(UUIDPKMixin, TimestampMixin, Base):
    """One-to-one with User — docs/DATABASE.md §2.1."""

    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")

    # Deliberately no `education`/`experience`/`projects`/`user_skills` relationships here.
    # Those child tables use soft delete (docs/DATABASE.md §1), and a relationship whose
    # `primaryjoin` filters on `deleted_at IS NULL` interacts awkwardly with
    # `cascade="all, delete-orphan"` (append/remove semantics get subtle once the collection
    # doesn't mirror the raw FK). The profile router queries each child table directly with
    # an explicit `deleted_at IS NULL` filter instead — one obvious code path rather than an
    # ORM relationship with edge cases.
