import uuid

import pytest
from httpx import AsyncClient

import app.api.v1.resumes as resumes_module
import app.workers.resume_tasks as resume_tasks_module
from app.core.db import AsyncSessionLocal
from app.models.resume import Resume, ResumeStatus
from app.schemas.resume import ResumeExtraction
from app.workers.resume_tasks import _process_resume


async def _noop_upload(path: str, content: bytes, content_type: str) -> None:
    return None


async def _noop_signed_url(path: str, *, expires_in: int = 3600) -> str:
    return f"https://example.com/signed/{path}"


@pytest.fixture(autouse=True)
def _stub_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Storage tests don't hit real Supabase — CI has no SUPABASE_URL/SECRET_KEY configured
    (docs/CONTRIBUTING.md), and even locally these should stay fast/deterministic."""
    monkeypatch.setattr(resumes_module, "upload_object", _noop_upload)
    monkeypatch.setattr(resumes_module, "create_signed_url", _noop_signed_url)


async def test_resumes_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/resumes")
    assert response.status_code == 401


async def test_upload_rejects_unsupported_file_type(authed_client: AsyncClient) -> None:
    response = await authed_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.txt", b"just some text", "text/plain")},
    )
    assert response.status_code == 422


async def test_upload_rejects_oversized_file(
    authed_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(resumes_module, "MAX_UPLOAD_BYTES", 10)
    response = await authed_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"way more than ten bytes of content", "application/pdf")},
    )
    assert response.status_code == 422


async def test_upload_rejects_empty_file(authed_client: AsyncClient) -> None:
    response = await authed_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 422


async def test_upload_list_status_and_delete_lifecycle(authed_client: AsyncClient) -> None:
    upload = await authed_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake but non-empty content", "application/pdf")},
    )
    assert upload.status_code == 202
    body = upload.json()["data"]
    assert body["status"] == "uploaded"
    resume_id = body["id"]

    listing = await authed_client.get("/api/v1/resumes")
    assert any(r["id"] == resume_id for r in listing.json()["data"])

    status_response = await authed_client.get(f"/api/v1/resumes/{resume_id}/status")
    assert status_response.json()["data"]["status"] == "uploaded"

    detail = await authed_client.get(f"/api/v1/resumes/{resume_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["file_download_url"]

    delete = await authed_client.delete(f"/api/v1/resumes/{resume_id}")
    assert delete.status_code == 204

    after = await authed_client.get(f"/api/v1/resumes/{resume_id}")
    assert after.status_code == 404


async def test_analyze_requires_idempotency_key(authed_client: AsyncClient) -> None:
    upload = await authed_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake but non-empty content", "application/pdf")},
    )
    resume_id = upload.json()["data"]["id"]

    response = await authed_client.post(f"/api/v1/resumes/{resume_id}/analyze")
    assert response.status_code == 400


async def test_analyze_conflicts_when_already_processing(authed_client: AsyncClient) -> None:
    upload = await authed_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake but non-empty content", "application/pdf")},
    )
    resume_id = upload.json()["data"]["id"]

    async with AsyncSessionLocal() as db:
        resume = await db.get(Resume, uuid.UUID(resume_id))
        assert resume is not None
        resume.status = ResumeStatus.PROCESSING
        await db.commit()

    response = await authed_client.post(
        f"/api/v1/resumes/{resume_id}/analyze", headers={"Idempotency-Key": "test-key-1"}
    )
    assert response.status_code == 409


async def test_full_processing_pipeline_scores_and_syncs_skills(
    authed_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_extraction = ResumeExtraction(
        full_name="Test User",
        skills=["Python", "SQL"],
        experience=[],
        education=[],
        projects=[],
    )

    async def _fake_download(path: str) -> bytes:
        return b"dummy bytes"

    def _fake_extract_text(content: bytes, file_type) -> str:  # noqa: ANN001
        return "Experience\nEducation\nSkills\nPython SQL"

    async def _fake_extract_fields(raw_text: str) -> ResumeExtraction:
        return fake_extraction

    monkeypatch.setattr(resume_tasks_module, "download_object", _fake_download)
    monkeypatch.setattr(resume_tasks_module, "extract_text", _fake_extract_text)
    monkeypatch.setattr(resume_tasks_module, "extract_resume_fields", _fake_extract_fields)

    upload = await authed_client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4 fake but non-empty content", "application/pdf")},
    )
    resume_id = uuid.UUID(upload.json()["data"]["id"])

    await _process_resume(resume_id)

    async with AsyncSessionLocal() as db:
        resume = await db.get(Resume, resume_id)
        assert resume is not None
        assert resume.status == ResumeStatus.COMPLETED
        assert resume.overall_score is not None
        assert resume.score_breakdown is not None

        versions = await authed_client.get(f"/api/v1/resumes/{resume_id}/versions")
        assert len(versions.json()["data"]) == 1

        skills_response = await authed_client.get("/api/v1/profile/skills")
        skill_names = {s["name"] for s in skills_response.json()["data"]}
        assert {"Python", "SQL"} <= skill_names
        assert all(s["source"] == "resume" for s in skills_response.json()["data"])
