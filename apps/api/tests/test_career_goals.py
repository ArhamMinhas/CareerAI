from httpx import AsyncClient


async def test_career_goal_crud_lifecycle(authed_client: AsyncClient) -> None:
    create = await authed_client.post(
        "/api/v1/career-goals",
        json={
            "target_role": "AI Engineer",
            "target_industry": "Tech",
            "target_years_experience": 3,
        },
    )
    assert create.status_code == 201
    body = create.json()["data"]
    assert body["target_role"] == "AI Engineer"
    assert body["is_active"] is True
    goal_id = body["id"]

    listing = await authed_client.get("/api/v1/career-goals")
    assert any(g["id"] == goal_id for g in listing.json()["data"])

    update = await authed_client.patch(f"/api/v1/career-goals/{goal_id}", json={"is_active": False})
    assert update.status_code == 200
    assert update.json()["data"]["is_active"] is False
    assert update.json()["data"]["target_role"] == "AI Engineer"

    delete = await authed_client.delete(f"/api/v1/career-goals/{goal_id}")
    assert delete.status_code == 204

    listing_after = await authed_client.get("/api/v1/career-goals")
    assert all(g["id"] != goal_id for g in listing_after.json()["data"])


async def test_career_goal_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/career-goals")
    assert response.status_code == 401


async def test_career_goal_not_found_for_missing_id(authed_client: AsyncClient) -> None:
    response = await authed_client.delete(
        "/api/v1/career-goals/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
