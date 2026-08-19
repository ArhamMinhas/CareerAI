"""Import every model here so `Base.metadata` is fully populated for Alembic autogenerate
(docs/DATABASE.md §5). Add new models to this list as they're introduced in later phases."""

from app.models.profile import Profile
from app.models.user import Role, User

__all__ = ["Profile", "Role", "User"]
