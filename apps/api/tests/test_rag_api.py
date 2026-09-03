import uuid

import pytest
from httpx import AsyncClient

import app.api.v1.rag as rag_module
from app.ai.llm.base import LLMResult
from app.ai.rag_answer import RagAnswerError
from app.core.config import settings
from app.schemas.rag import RagCitation

# No Redis key cleanup fixtures here (unlike tests/test_embeddings.py's content-hash cache,
# which real requests could later collide with): `authed_client` mints a fresh random user per
# test, so every rate-limit/idempotency key this file touches is unique and irrelevant to any
# other test or real traffic — the reservation (120s) and response (24h) TTLs expire on their own.


class _FakeAnswerCounter:
    """Stands in for `answer_question` — counts real calls so tests can assert idempotency
    replay/conflict paths never trigger a second (paid) LLM call."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, db: object, question: str) -> tuple[str, list[RagCitation], LLMResult]:
        self.calls += 1
        return (
            f"Answer to: {question}",
            [RagCitation(resource_slug="test-slug", resource_title="Test Title")],
            LLMResult(
                text="raw",
                parsed=None,
                model="test-model",
                prompt_tokens=1,
                completion_tokens=1,
                latency_ms=1,
            ),
        )


async def _fake_failing_answer(db: object, question: str) -> tuple[str, list, LLMResult]:
    raise RagAnswerError("provider is down")


async def test_rag_query_requires_idempotency_key_header(authed_client: AsyncClient) -> None:
    response = await authed_client.post("/api/v1/rag/query", json={"question": "How do I start?"})
    assert response.status_code == 400


async def test_rag_query_returns_grounded_answer_with_citations(
    monkeypatch: pytest.MonkeyPatch, authed_client: AsyncClient
) -> None:
    fake = _FakeAnswerCounter()
    monkeypatch.setattr(rag_module, "answer_question", fake)
    idempotency_key = str(uuid.uuid4())

    response = await authed_client.post(
        "/api/v1/rag/query",
        json={"question": "How do I write a good resume bullet?"},
        headers={"Idempotency-Key": idempotency_key},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer"] == "Answer to: How do I write a good resume bullet?"
    assert data["citations"] == [{"resource_slug": "test-slug", "resource_title": "Test Title"}]
    assert fake.calls == 1


async def test_rag_query_replays_cached_response_for_repeated_idempotency_key(
    monkeypatch: pytest.MonkeyPatch, authed_client: AsyncClient
) -> None:
    fake = _FakeAnswerCounter()
    monkeypatch.setattr(rag_module, "answer_question", fake)
    idempotency_key = str(uuid.uuid4())
    body = {"question": "How do I negotiate an offer?"}
    headers = {"Idempotency-Key": idempotency_key}

    first = await authed_client.post("/api/v1/rag/query", json=body, headers=headers)
    second = await authed_client.post("/api/v1/rag/query", json=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    assert fake.calls == 1  # the second request replayed the cached response, no second LLM call


async def test_rag_query_502s_when_generation_fails(
    monkeypatch: pytest.MonkeyPatch, authed_client: AsyncClient
) -> None:
    monkeypatch.setattr(rag_module, "answer_question", _fake_failing_answer)

    response = await authed_client.post(
        "/api/v1/rag/query",
        json={"question": "A question that will fail."},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 502


async def test_rag_query_429s_with_retry_after_once_rate_limit_is_exhausted(
    monkeypatch: pytest.MonkeyPatch, authed_client: AsyncClient
) -> None:
    monkeypatch.setattr(settings, "rate_limit_ai_per_minute", 1)
    fake = _FakeAnswerCounter()
    monkeypatch.setattr(rag_module, "answer_question", fake)

    first = await authed_client.post(
        "/api/v1/rag/query",
        json={"question": "First question."},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert first.status_code == 200

    second = await authed_client.post(
        "/api/v1/rag/query",
        json={"question": "Second question, different key."},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert second.status_code == 429
    assert "Retry-After" in second.headers
    assert int(second.headers["Retry-After"]) >= 1
    assert fake.calls == 1  # the rate-limited request never reached answer_question
