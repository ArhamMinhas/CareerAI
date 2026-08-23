from httpx import AsyncClient

from app.models.job import Job


async def test_post_job_match_computes_ranked_matches(
    authed_client: AsyncClient, seeded_job: Job
) -> None:
    response = await authed_client.post("/api/v1/jobs/match")
    assert response.status_code == 200
    matches = response.json()["data"]
    assert any(m["job"]["id"] == str(seeded_job.id) for m in matches)

    match = next(m for m in matches if m["job"]["id"] == str(seeded_job.id))
    assert 0 <= match["match_score"] <= 100
    breakdown = match["score_breakdown"]
    expected_components = {
        "semantic_similarity",
        "skill_overlap",
        "experience_match",
        "education_match",
        "preference_match",
        "location_match",
    }
    assert set(breakdown) == expected_components
    for component in breakdown.values():
        assert component["explanation"]
        assert 0 <= component["score"] <= 100
    assert round(sum(c["weight"] for c in breakdown.values()), 6) == 1.0
    assert match["explanation"]


async def test_get_job_matches_reads_stored_results(
    authed_client: AsyncClient, seeded_job: Job
) -> None:
    refresh = await authed_client.post("/api/v1/jobs/match")
    assert refresh.status_code == 200

    stored = await authed_client.get("/api/v1/matches")
    assert stored.status_code == 200
    assert any(m["job"]["id"] == str(seeded_job.id) for m in stored.json()["data"])


async def test_job_match_endpoints_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/matches")).status_code == 401
    assert (await client.post("/api/v1/jobs/match")).status_code == 401
