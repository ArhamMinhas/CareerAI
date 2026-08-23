import uuid

from httpx import AsyncClient

from app.models.job import Job


async def test_application_crud_lifecycle(authed_client: AsyncClient, seeded_job: Job) -> None:
    create = await authed_client.post("/api/v1/applications", json={"job_id": str(seeded_job.id)})
    assert create.status_code == 201
    body = create.json()["data"]
    assert body["status"] == "saved"
    assert body["job"]["id"] == str(seeded_job.id)
    application_id = body["id"]

    listing = await authed_client.get("/api/v1/applications")
    assert any(a["id"] == application_id for a in listing.json()["data"]["applications"])

    update = await authed_client.patch(
        f"/api/v1/applications/{application_id}",
        json={"status": "applied", "applied_at": "2026-01-01T00:00:00Z"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["status"] == "applied"

    delete = await authed_client.delete(f"/api/v1/applications/{application_id}")
    assert delete.status_code == 204

    listing_after = await authed_client.get("/api/v1/applications")
    assert all(a["id"] != application_id for a in listing_after.json()["data"]["applications"])


async def test_create_application_conflicts_on_duplicate(
    authed_client: AsyncClient, seeded_job: Job
) -> None:
    first = await authed_client.post("/api/v1/applications", json={"job_id": str(seeded_job.id)})
    assert first.status_code == 201

    duplicate = await authed_client.post(
        "/api/v1/applications", json={"job_id": str(seeded_job.id)}
    )
    assert duplicate.status_code == 409

    await authed_client.delete(f"/api/v1/applications/{first.json()['data']['id']}")


async def test_create_application_after_delete_does_not_conflict(
    authed_client: AsyncClient, seeded_job: Job
) -> None:
    """Regression test for the partial-unique-index fix: soft-deleting a tracked application
    must free up its (user_id, job_id) pair for a fresh insert, not collide with the old,
    soft-deleted row."""
    first = await authed_client.post("/api/v1/applications", json={"job_id": str(seeded_job.id)})
    assert first.status_code == 201
    first_id = first.json()["data"]["id"]

    delete = await authed_client.delete(f"/api/v1/applications/{first_id}")
    assert delete.status_code == 204

    second = await authed_client.post("/api/v1/applications", json={"job_id": str(seeded_job.id)})
    assert second.status_code == 201
    assert second.json()["data"]["id"] != first_id

    await authed_client.delete(f"/api/v1/applications/{second.json()['data']['id']}")


async def test_create_application_404_for_unknown_job(authed_client: AsyncClient) -> None:
    response = await authed_client.post("/api/v1/applications", json={"job_id": str(uuid.uuid4())})
    assert response.status_code == 404


async def test_application_not_found_for_other_users_row(authed_client: AsyncClient) -> None:
    response = await authed_client.patch(
        f"/api/v1/applications/{uuid.uuid4()}", json={"status": "applied"}
    )
    assert response.status_code == 404


async def test_applications_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/applications")
    assert response.status_code == 401
