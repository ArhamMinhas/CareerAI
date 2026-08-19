import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.profile import Profile


class Role(enum.StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    RECRUITER = "RECRUITER"


class User(UUIDPKMixin, TimestampMixin, Base):
    """Local identity row, keyed by the Supabase Auth user id (the JWT `sub` claim).

    Supabase owns credentials/verification/OAuth; this table owns app-level authorization
    (role) and anything joined against from the rest of the schema — see docs/SECURITY.md §1-2
    and docs/DATABASE.md §2.1. Deliberately has no password column: this app never stores or
    verifies credentials itself.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), default=Role.USER, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped["Profile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
