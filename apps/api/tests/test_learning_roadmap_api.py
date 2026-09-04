import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

import app.api.v1.learning_roadmap as learning_roadmap_module
from app.ai.llm.base import LLMResult
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.skill import Skill
from app.models.skill_gap import SkillGap
from app.services.skill_taxonomy import get_or_create_skill

# Fully self-contained — real LLM calls are always monkeypatched out. Real Redis rate-limit/
# idempotency keys are used, but `authed_client` mints a fresh random user per test, so they
# never collide with other tests or real traffic (same reasoning as tests/test_rag_api.py).


async def _fake_overview_success(target_role: str, sequenced: list) -> tuple[str, LLMResult]:
    return "A generated overview.", LLMResult(
        text="raw",
        parsed=None,
        model="test-model",
        prompt_tokens=1,
        completion_tokens=1,
        latency_ms=1,
    )


async def _fake_overview_failure(target_role: str, sequenced: list) -> None:
    return None


@pytest.fixture
async def roadmap_api_career_path() -> AsyncGenerator[tuple[CareerPath, Skill]]:
    unique = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        skill = await get_or_create_skill(db, f"Roadmap API Skill {unique}")
        await db.commit()

        path = CareerPath(
            slug=f"test-roadmap-api-path-{unique}",
            title=f"Test Roadmap API Path {unique}",
            summary="A test career path for learning-roadmap API tests.",
            description_md="Test description.",
            related_job_titles=[],
            published=True,
        )
        db.add(path)
        await db.flush()
        db.add(CareerPathSkill(career_path_id=path.id, skill_id=skill.id, weight=5, is_core=False))
        await db.commit()
        path_id, skill_id = path.id, skill.id

    yield path, skill

    async with AsyncSessionLocal() as db:
        await db.execute(delete(SkillGap).where(SkillGap.skill_id == skill_id))
        await db.execute(delete(CareerPath).where(CareerPath.id == path_id))
        await db.execute(delete(Skill).where(Skill.id == skill_id))
        await db.commit()


async def test_get_roadmap_404_before_generation(
    authed_client: AsyncClient, roadmap_api_career_path: tuple[CareerPath, Skill]
) -> None:
    path, _skill = roadmap_api_career_path
    response = await authed_client.get(f"/api/v1/learning-roadmap?target_role={path.slug}")
    assert response.status_code == 404


async def test_generate_roadmap_requires_idempotency_key_header(
    authed_client: AsyncClient, roadmap_api_career_path: tuple[CareerPath, Skill]
) -> None:
    path, _skill = roadmap_api_career_path
    response = await authed_client.post(
        f"/api/v1/learning-roadmap/generate?target_role={path.slug}"
    )
    assert response.status_code == 400


async def test_generate_roadmap_404_for_unknown_target_role(authed_client: AsyncClient) -> None:
    response = await authed_client.post(
        "/api/v1/learning-roadmap/generate?target_role=totally-unknown-role-xyz",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 404


async def test_generate_then_get_roundtrip_with_real_sequence_and_overview(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    roadmap_api_career_path: tuple[CareerPath, Skill],
) -> None:
    path, skill = roadmap_api_career_path
    monkeypatch.setattr(learning_roadmap_module, "generate_overview", _fake_overview_success)

    generate_response = await authed_client.post(
        f"/api/v1/learning-roadmap/generate?target_role={path.slug}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert generate_response.status_code == 200
    data = generate_response.json()["data"]
    assert data["target_role"] == path.slug
    assert data["overview"] == "A generated overview."
    assert data["progress"] == {"completed": 0, "total": 1}
    assert len(data["items"]) == 1
    assert data["items"][0]["skill"]["name"] == skill.name
    assert data["items"][0]["completed"] is False

    get_response = await authed_client.get(f"/api/v1/learning-roadmap?target_role={path.slug}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == data["id"]


async def test_generate_roadmap_succeeds_even_when_llm_overview_fails(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    roadmap_api_career_path: tuple[CareerPath, Skill],
) -> None:
    """The specific regression the Plan-agent critique caught: the LLM overview call failing
    must never turn into a 502 for this route — generation (the deterministic, actually-valuable
    part) still succeeds and commits, with `overview` staying null."""
    path, _skill = roadmap_api_career_path
    monkeypatch.setattr(learning_roadmap_module, "generate_overview", _fake_overview_failure)

    response = await authed_client.post(
        f"/api/v1/learning-roadmap/generate?target_role={path.slug}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["overview"] is None
    assert len(data["items"]) == 1


async def test_generate_roadmap_replays_cached_response_for_repeated_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    roadmap_api_career_path: tuple[CareerPath, Skill],
) -> None:
    path, _skill = roadmap_api_career_path
    calls = {"count": 0}

    async def _counting_overview(target_role: str, sequenced: list) -> tuple[str, LLMResult]:
        calls["count"] += 1
        return await _fake_overview_success(target_role, sequenced)

    monkeypatch.setattr(learning_roadmap_module, "generate_overview", _counting_overview)
    idempotency_key = str(uuid.uuid4())
    url = f"/api/v1/learning-roadmap/generate?target_role={path.slug}"
    headers = {"Idempotency-Key": idempotency_key}

    first = await authed_client.post(url, headers=headers)
    second = await authed_client.post(url, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    assert calls["count"] == 1  # the second request replayed the cached response


async def test_generate_roadmap_429s_with_retry_after_once_rate_limit_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    roadmap_api_career_path: tuple[CareerPath, Skill],
) -> None:
    path, _skill = roadmap_api_career_path
    monkeypatch.setattr(settings, "rate_limit_ai_per_minute", 1)
    monkeypatch.setattr(learning_roadmap_module, "generate_overview", _fake_overview_success)
    url = f"/api/v1/learning-roadmap/generate?target_role={path.slug}"

    first = await authed_client.post(url, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert first.status_code == 200

    second = await authed_client.post(url, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert second.status_code == 429
    assert "Retry-After" in second.headers


async def test_patch_item_toggles_completion_and_returns_full_roadmap(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    roadmap_api_career_path: tuple[CareerPath, Skill],
) -> None:
    path, _skill = roadmap_api_career_path
    monkeypatch.setattr(learning_roadmap_module, "generate_overview", _fake_overview_success)

    generate_response = await authed_client.post(
        f"/api/v1/learning-roadmap/generate?target_role={path.slug}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    item_id = generate_response.json()["data"]["items"][0]["id"]

    patch_response = await authed_client.patch(
        f"/api/v1/learning-roadmap/items/{item_id}", json={"completed": True}
    )
    assert patch_response.status_code == 200
    data = patch_response.json()["data"]
    assert data["items"][0]["completed"] is True
    assert data["progress"] == {"completed": 1, "total": 1}
    assert data["status"] == "completed"  # single item, now fully complete


async def test_patch_item_404_for_unknown_item(authed_client: AsyncClient) -> None:
    response = await authed_client.patch(
        f"/api/v1/learning-roadmap/items/{uuid.uuid4()}", json={"completed": True}
    )
    assert response.status_code == 404


async def test_delete_then_get_404s_and_regenerate_works(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    roadmap_api_career_path: tuple[CareerPath, Skill],
) -> None:
    path, _skill = roadmap_api_career_path
    monkeypatch.setattr(learning_roadmap_module, "generate_overview", _fake_overview_success)

    await authed_client.post(
        f"/api/v1/learning-roadmap/generate?target_role={path.slug}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    delete_response = await authed_client.delete(
        f"/api/v1/learning-roadmap?target_role={path.slug}"
    )
    assert delete_response.status_code == 204

    get_response = await authed_client.get(f"/api/v1/learning-roadmap?target_role={path.slug}")
    assert get_response.status_code == 404

    regenerate_response = await authed_client.post(
        f"/api/v1/learning-roadmap/generate?target_role={path.slug}",
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert regenerate_response.status_code == 200


async def test_delete_roadmap_404_when_nothing_to_delete(
    authed_client: AsyncClient, roadmap_api_career_path: tuple[CareerPath, Skill]
) -> None:
    path, _skill = roadmap_api_career_path
    response = await authed_client.delete(f"/api/v1/learning-roadmap?target_role={path.slug}")
    assert response.status_code == 404


async def test_roadmap_routes_require_auth(
    client: AsyncClient, roadmap_api_career_path: tuple[CareerPath, Skill]
) -> None:
    path, _skill = roadmap_api_career_path
    assert (
        await client.get(f"/api/v1/learning-roadmap?target_role={path.slug}")
    ).status_code == 401
    assert (
        await client.post(f"/api/v1/learning-roadmap/generate?target_role={path.slug}")
    ).status_code == 401
