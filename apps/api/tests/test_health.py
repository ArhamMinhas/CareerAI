from httpx import AsyncClient


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["meta"]["request_id"] is not None
    assert response.headers["X-Request-ID"] == body["meta"]["request_id"]
