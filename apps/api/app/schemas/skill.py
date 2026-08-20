import uuid

from pydantic import BaseModel, ConfigDict


class SkillRead(BaseModel):
    """Taxonomy entry — used for the `/skills?q=` autocomplete backing manual skill entry.
    The full taxonomy browse/gap-analysis surface (docs/API.md §5 "Skills") is Phase 6."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    category: str | None
