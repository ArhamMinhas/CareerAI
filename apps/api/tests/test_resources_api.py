import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

from app.core.db import AsyncSessionLocal
from app.models.kb_chunk import KbChunk
from app.models.resource import Resource

# Fully self-contained fixtures — must not depend on app/scripts/seed_resources.py having run.
# Embeddings are hand-written vectors, not real API calls, same convention as test_career_paths.py.


@pytest.fixture
async def seeded_resources() -> AsyncGenerator[tuple[Resource, Resource, Resource]]:
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        published_a = Resource(
            slug=f"test-resource-a-{unique}",
            title=f"Test Resource A {unique}",
            summary="Summary A",
            body_md="## Heading\n\nBody A.",
            category="testing",
            tags=["a", "b"],
            embedding=[0.1] * 1536,
            published=True,
        )
        published_b = Resource(
            slug=f"test-resource-b-{unique}",
            title=f"Test Resource B {unique}",
            summary="Summary B",
            body_md="## Heading\n\nBody B.",
            embedding=[0.101] * 1536,  # deliberately close to published_a's vector
            published=True,
        )
        draft = Resource(
            slug=f"test-resource-draft-{unique}",
            title=f"Test Resource Draft {unique}",
            summary="Summary Draft",
            body_md="## Heading\n\nBody Draft.",
            embedding=[0.1] * 1536,
            published=False,
        )
        db.add_all([published_a, published_b, draft])
        await db.commit()
        ids = (published_a.id, published_b.id, draft.id)

    yield published_a, published_b, draft

    async with AsyncSessionLocal() as db:
        await db.execute(delete(KbChunk).where(KbChunk.resource_id.in_(ids)))
        await db.execute(delete(Resource).where(Resource.id.in_(ids)))
        await db.commit()


async def test_list_resources_is_public_and_excludes_drafts(
    client: AsyncClient,
    seeded_resources: tuple[Resource, Resource, Resource],
) -> None:
    published_a, published_b, draft = seeded_resources
    response = await client.get("/api/v1/resources")
    assert response.status_code == 200
    slugs = {item["slug"] for item in response.json()["data"]}
    assert published_a.slug in slugs
    assert published_b.slug in slugs
    assert draft.slug not in slugs


async def test_get_resource_detail_includes_related_resources(
    client: AsyncClient,
    seeded_resources: tuple[Resource, Resource, Resource],
) -> None:
    published_a, published_b, draft = seeded_resources
    response = await client.get(f"/api/v1/resources/{published_a.slug}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == published_a.title
    assert data["body_md"] == published_a.body_md
    related_slugs = {r["slug"] for r in data["related_resources"]}
    assert published_b.slug in related_slugs
    assert published_a.slug not in related_slugs
    assert draft.slug not in related_slugs


async def test_get_resource_detail_404_for_draft_slug(
    client: AsyncClient,
    seeded_resources: tuple[Resource, Resource, Resource],
) -> None:
    """A draft resource is queryable internally but never served by the public API — same
    `published` gate as `CareerPath`."""
    _, _, draft = seeded_resources
    response = await client.get(f"/api/v1/resources/{draft.slug}")
    assert response.status_code == 404


async def test_get_resource_detail_404_for_unknown_slug(client: AsyncClient) -> None:
    response = await client.get("/api/v1/resources/not-a-real-resource")
    assert response.status_code == 404
