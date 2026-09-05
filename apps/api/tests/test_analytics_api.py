from httpx import AsyncClient

# Fully self-contained — no LLM calls anywhere in this feature (docs/AI_ARCHITECTURE.md §8 has no
# Analytics agent), so unlike test_rag_api.py/test_interviews_api.py there's nothing to
# monkeypatch. These routes are also read-only and idempotent by nature (repeated GETs never
# mutate state), so there's no idempotency-key/rate-limit surface to test either.


async def test_market_analytics_returns_a_well_formed_envelope(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/analytics/market")
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data["top_growing_skills"], list)
    assert isinstance(data["job_posting_trend"], list)
    assert isinstance(data["salary_trend"], list)
    assert isinstance(data["trending_career_paths"], list)


async def test_market_analytics_accepts_date_range_filter(authed_client: AsyncClient) -> None:
    response = await authed_client.get(
        "/api/v1/analytics/market?date_from=2020-01-01&date_to=2020-12-31"
    )
    assert response.status_code == 200
    data = response.json()["data"]
    # A date range far in the past, before any real seeded job/salary data, must return an
    # honestly empty time series, not crash or return unfiltered data.
    assert data["job_posting_trend"] == []
    assert data["salary_trend"] == []


async def test_market_analytics_rejects_malformed_date(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/analytics/market?date_from=not-a-date")
    assert response.status_code == 422


async def test_skill_analytics_returns_rows_and_respects_limit(
    authed_client: AsyncClient,
) -> None:
    response = await authed_client.get("/api/v1/analytics/skills?limit=5")
    assert response.status_code == 200
    rows = response.json()["data"]["rows"]
    assert len(rows) <= 5
    if rows:
        row = rows[0]
        assert {"skill_id", "skill_name", "skill_slug", "demand_count", "growth_rate"} <= set(row)


async def test_skill_analytics_falls_back_to_a_valid_sort_for_an_unknown_sort_value(
    authed_client: AsyncClient,
) -> None:
    response = await authed_client.get("/api/v1/analytics/skills?sort=not-a-real-sort&limit=5")
    assert response.status_code == 200


async def test_candidate_dashboard_returns_a_well_formed_envelope_for_a_fresh_user(
    authed_client: AsyncClient,
) -> None:
    """`authed_client` mints a brand-new throwaway user per test, so this exercises the
    empty-state path for real over HTTP, not just at the service layer."""
    response = await authed_client.get("/api/v1/analytics/dashboard")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resume"] == {"status": None, "overall_score": None}
    assert data["skill_gaps"] is None
    assert data["interviews"] == {"total_completed": 0, "average_overall_score": None}
    assert data["roadmap"] is None
    assert data["applications"]["total_matches"] == 0


async def test_analytics_routes_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/analytics/market")).status_code == 401
    assert (await client.get("/api/v1/analytics/skills")).status_code == 401
    assert (await client.get("/api/v1/analytics/dashboard")).status_code == 401
