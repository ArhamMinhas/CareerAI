import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResourceRead(BaseModel):
    """List-view projection — `/api/v1/resources`, the public `/resources` index page, and
    `sitemap.ts` (which needs `updated_at` for a real `lastModified`, not a hardcoded
    `new Date()` — see docs/SEO.md)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    summary: str
    category: str | None
    tags: list[str] | None
    updated_at: datetime


class ResourceDetailRead(ResourceRead):
    """`/api/v1/resources/{slug}` and the public `/resources/[slug]` page.
    `related_resources` isn't an ORM relationship — populated by the route after validation, via
    embedding cosine similarity (app/services/resources.py), same pattern as
    `CareerPathDetailRead.related_career_paths`."""

    body_md: str
    related_resources: list[ResourceRead] = Field(default_factory=list)
