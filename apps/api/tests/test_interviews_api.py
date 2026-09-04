import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import delete

import app.api.v1.interviews as interviews_module
from app.ai.interview_evaluation import InterviewEvaluationError, InterviewEvaluationResult
from app.ai.llm.base import LLMResult
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models.interview import InterviewMode, InterviewQuestionBank

# Fully self-contained — real LLM calls are always monkeypatched out (`evaluate_answer` is the
# one real call this feature makes). Real Redis rate-limit/idempotency keys are used, but
# `authed_client` mints a fresh random user per test, so they never collide with other tests or
# real traffic (same reasoning as tests/test_rag_api.py). Deliberately does NOT depend on
# `seed_interview_questions.py` having run — CI (.github/workflows/ci.yml) only runs `alembic
# upgrade head`, never the seed script, so these tests insert their own throwaway bank content
# for InterviewMode.HR rather than relying on any real seeded question existing.

_MODE = InterviewMode.HR


async def _fake_evaluate_success(
    *, mode: InterviewMode, question_text: str, answer_text: str, resume_context: str | None
) -> tuple[InterviewEvaluationResult, LLMResult]:
    return (
        InterviewEvaluationResult(
            correctness_score=80, depth_score=70, communication_score=90, feedback="Solid answer."
        ),
        LLMResult(
            text="raw",
            parsed=None,
            model="test-model",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1,
        ),
    )


async def _fake_evaluate_failure(
    *, mode: InterviewMode, question_text: str, answer_text: str, resume_context: str | None
) -> tuple[InterviewEvaluationResult, LLMResult]:
    raise InterviewEvaluationError("provider is down")


@pytest.fixture
async def interview_bank_questions() -> AsyncGenerator[InterviewMode]:
    """Inserts 6 throwaway `InterviewQuestionBank` rows for `_MODE` (one more than
    `_QUESTIONS_PER_INTERVIEW=5`, so a full 5-question session never needs the category-repeat
    fallback) and deletes only the rows it inserted afterward — never a blanket delete-by-mode,
    so this stays safe to run alongside any real seeded content that may already exist."""
    ids: list[uuid.UUID] = []
    async with AsyncSessionLocal() as db:
        for i in range(6):
            row = InterviewQuestionBank(
                mode=_MODE,
                category=f"api-test-cat-{i}",
                question_text=f"API test question {i} {uuid.uuid4().hex[:8]}",
            )
            db.add(row)
            await db.flush()
            ids.append(row.id)
        await db.commit()

    yield _MODE

    async with AsyncSessionLocal() as db:
        await db.execute(delete(InterviewQuestionBank).where(InterviewQuestionBank.id.in_(ids)))
        await db.commit()


async def test_start_interview_creates_session_with_first_question(
    authed_client: AsyncClient, interview_bank_questions: InterviewMode
) -> None:
    response = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mode"] == _MODE.value
    assert data["status"] == "in_progress"
    assert data["target_role"] is None
    assert len(data["questions"]) == 1
    assert data["questions"][0]["order_index"] == 0
    assert data["questions"][0]["answer"] is None


async def test_start_interview_does_not_require_idempotency_key(
    authed_client: AsyncClient, interview_bank_questions: InterviewMode
) -> None:
    """No LLM call happens at session creation, so unlike `.../answer`, repeated calls with no
    Idempotency-Key header are never deduped — each POST genuinely creates a new session."""
    first = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    second = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["id"] != second.json()["data"]["id"]


async def test_list_interview_history_pagination_round_trips(
    authed_client: AsyncClient, interview_bank_questions: InterviewMode
) -> None:
    for _ in range(3):
        await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})

    first_page = await authed_client.get("/api/v1/interviews?limit=2")
    assert first_page.status_code == 200
    body = first_page.json()
    assert len(body["data"]) == 2
    cursor = body["meta"]["next_cursor"]
    assert cursor is not None

    second_page = await authed_client.get(f"/api/v1/interviews?limit=2&cursor={cursor}")
    assert second_page.status_code == 200
    body_two = second_page.json()
    assert len(body_two["data"]) == 1
    assert body_two["meta"]["next_cursor"] is None


async def test_list_interview_history_400s_on_invalid_cursor(authed_client: AsyncClient) -> None:
    response = await authed_client.get("/api/v1/interviews?cursor=not-a-real-cursor")
    assert response.status_code == 400


async def test_get_interview_analytics_is_empty_before_any_completed_session(
    authed_client: AsyncClient,
) -> None:
    response = await authed_client.get("/api/v1/interviews/analytics")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_completed"] == 0
    assert data["average_overall_score"] is None
    assert data["recent"] == []


async def test_get_interview_404_for_missing(authed_client: AsyncClient) -> None:
    response = await authed_client.get(f"/api/v1/interviews/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_submit_answer_requires_idempotency_key_header(
    authed_client: AsyncClient, interview_bank_questions: InterviewMode
) -> None:
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    data = start.json()["data"]
    question_id = data["questions"][0]["id"]

    response = await authed_client.post(
        f"/api/v1/interviews/{data['id']}/answer",
        json={"question_id": question_id, "answer_text": "My answer", "response_time_seconds": 10},
    )
    assert response.status_code == 400


async def test_submit_answer_advances_to_next_question(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    interview_bank_questions: InterviewMode,
) -> None:
    monkeypatch.setattr(interviews_module, "evaluate_answer", _fake_evaluate_success)
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    data = start.json()["data"]
    question_id = data["questions"][0]["id"]

    response = await authed_client.post(
        f"/api/v1/interviews/{data['id']}/answer",
        json={"question_id": question_id, "answer_text": "My answer", "response_time_seconds": 10},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "in_progress"
    assert len(result["questions"]) == 2
    answered = result["questions"][0]
    assert answered["answer"]["answer_text"] == "My answer"
    assert answered["answer"]["evaluation"]["correctness_score"] == 80
    assert answered["answer"]["evaluation"]["feedback"] == "Solid answer."
    assert result["questions"][1]["answer"] is None


async def test_submit_answer_replays_cached_response_for_repeated_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    interview_bank_questions: InterviewMode,
) -> None:
    calls = {"count": 0}

    async def _counting_evaluate(
        *, mode: InterviewMode, question_text: str, answer_text: str, resume_context: str | None
    ) -> tuple[InterviewEvaluationResult, LLMResult]:
        calls["count"] += 1
        return await _fake_evaluate_success(
            mode=mode,
            question_text=question_text,
            answer_text=answer_text,
            resume_context=resume_context,
        )

    monkeypatch.setattr(interviews_module, "evaluate_answer", _counting_evaluate)
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    data = start.json()["data"]
    question_id = data["questions"][0]["id"]
    idempotency_key = str(uuid.uuid4())
    url = f"/api/v1/interviews/{data['id']}/answer"
    payload = {"question_id": question_id, "answer_text": "My answer", "response_time_seconds": 10}
    headers = {"Idempotency-Key": idempotency_key}

    first = await authed_client.post(url, json=payload, headers=headers)
    second = await authed_client.post(url, json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    assert calls["count"] == 1  # the second request replayed the cached response


async def test_submit_answer_409s_when_question_already_answered(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    interview_bank_questions: InterviewMode,
) -> None:
    monkeypatch.setattr(interviews_module, "evaluate_answer", _fake_evaluate_success)
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    data = start.json()["data"]
    question_id = data["questions"][0]["id"]
    url = f"/api/v1/interviews/{data['id']}/answer"
    payload = {"question_id": question_id, "answer_text": "My answer", "response_time_seconds": 10}

    first = await authed_client.post(
        url, json=payload, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert first.status_code == 200

    # A different Idempotency-Key targeting the *same, already-answered* question_id must not be
    # served from the idempotency cache (it's a fresh key) — it must hit the real 409 guard.
    second = await authed_client.post(
        url, json=payload, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert second.status_code == 409


async def test_submit_answer_404_for_unknown_question(
    authed_client: AsyncClient, interview_bank_questions: InterviewMode
) -> None:
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    data = start.json()["data"]

    response = await authed_client.post(
        f"/api/v1/interviews/{data['id']}/answer",
        json={
            "question_id": str(uuid.uuid4()),
            "answer_text": "My answer",
            "response_time_seconds": 10,
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 404


async def test_submit_answer_429s_with_retry_after_once_rate_limit_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    interview_bank_questions: InterviewMode,
) -> None:
    monkeypatch.setattr(interviews_module, "evaluate_answer", _fake_evaluate_success)
    monkeypatch.setattr(settings, "rate_limit_ai_per_minute", 1)
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    data = start.json()["data"]
    question_id = data["questions"][0]["id"]
    url = f"/api/v1/interviews/{data['id']}/answer"

    first = await authed_client.post(
        url,
        json={"question_id": question_id, "answer_text": "A", "response_time_seconds": 1},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert first.status_code == 200

    second_question_id = first.json()["data"]["questions"][1]["id"]
    second = await authed_client.post(
        url,
        json={"question_id": second_question_id, "answer_text": "B", "response_time_seconds": 1},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert second.status_code == 429
    assert "Retry-After" in second.headers


async def test_submit_answer_502s_when_evaluation_fails(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    interview_bank_questions: InterviewMode,
) -> None:
    """The deliberate opposite of learning_roadmap's swallow-and-continue: there's no
    deterministic fallback evaluation, so a genuine LLM failure must surface as a real error, not
    a silently-empty evaluation."""
    monkeypatch.setattr(interviews_module, "evaluate_answer", _fake_evaluate_failure)
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    data = start.json()["data"]
    question_id = data["questions"][0]["id"]

    response = await authed_client.post(
        f"/api/v1/interviews/{data['id']}/answer",
        json={"question_id": question_id, "answer_text": "My answer", "response_time_seconds": 10},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 502


async def test_full_session_completes_after_five_answers_with_real_overall_score(
    monkeypatch: pytest.MonkeyPatch,
    authed_client: AsyncClient,
    interview_bank_questions: InterviewMode,
) -> None:
    monkeypatch.setattr(interviews_module, "evaluate_answer", _fake_evaluate_success)
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    interview_id = start.json()["data"]["id"]
    next_question_id = start.json()["data"]["questions"][0]["id"]

    result_body = None
    for _ in range(5):
        response = await authed_client.post(
            f"/api/v1/interviews/{interview_id}/answer",
            json={
                "question_id": next_question_id,
                "answer_text": "An answer",
                "response_time_seconds": 15,
            },
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        assert response.status_code == 200
        result_body = response.json()["data"]
        unanswered = [q for q in result_body["questions"] if q["answer"] is None]
        if unanswered:
            next_question_id = unanswered[0]["id"]

    assert result_body is not None
    assert result_body["status"] == "completed"
    assert result_body["overall_score"] == pytest.approx(80.0)  # (80+70+90)/3, all 5 identical
    assert len(result_body["questions"]) == 5
    assert all(q["answer"] is not None for q in result_body["questions"])


async def test_delete_interview_then_get_404s(
    authed_client: AsyncClient, interview_bank_questions: InterviewMode
) -> None:
    start = await authed_client.post("/api/v1/interviews", json={"mode": _MODE.value})
    interview_id = start.json()["data"]["id"]

    delete_response = await authed_client.delete(f"/api/v1/interviews/{interview_id}")
    assert delete_response.status_code == 204

    get_response = await authed_client.get(f"/api/v1/interviews/{interview_id}")
    assert get_response.status_code == 404


async def test_delete_interview_404_when_nothing_to_delete(authed_client: AsyncClient) -> None:
    response = await authed_client.delete(f"/api/v1/interviews/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_interview_routes_require_auth(
    client: AsyncClient, interview_bank_questions: InterviewMode
) -> None:
    assert (await client.get("/api/v1/interviews")).status_code == 401
    assert (await client.get("/api/v1/interviews/analytics")).status_code == 401
    assert (await client.post("/api/v1/interviews", json={"mode": _MODE.value})).status_code == 401
    assert (await client.get(f"/api/v1/interviews/{uuid.uuid4()}")).status_code == 401
    assert (
        await client.post(
            f"/api/v1/interviews/{uuid.uuid4()}/answer",
            json={"question_id": str(uuid.uuid4()), "answer_text": "x", "response_time_seconds": 1},
        )
    ).status_code == 401
    assert (await client.delete(f"/api/v1/interviews/{uuid.uuid4()}")).status_code == 401
