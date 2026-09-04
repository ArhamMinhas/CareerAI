import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.interview_evaluation import InterviewEvaluationError, evaluate_answer
from app.core.db import get_db
from app.core.idempotency import get_cached_response, reserve, store_response
from app.core.pagination import InvalidCursorError
from app.core.rate_limit import RateLimitError, check_ai_rate_limit
from app.core.security import get_current_user
from app.models.interview import (
    Interview,
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewStatus,
)
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.interview import (
    InterviewAnalyticsRead,
    InterviewAnalyticsRecent,
    InterviewAnswerRead,
    InterviewAnswerRequest,
    InterviewCreateRequest,
    InterviewDetailRead,
    InterviewEvaluationRead,
    InterviewQuestionRead,
    InterviewRead,
)
from app.services.ai_conversations import AIFeature, log_conversation
from app.services.interviews import (
    AnswerAlreadySubmittedError,
    advance_or_complete,
    build_resume_context,
    create_interview,
    delete_interview,
    get_analytics,
    get_owned_interview,
    get_question_in_interview,
    get_questions_with_details,
    has_answer,
    list_interviews,
    record_answer,
)

router = APIRouter(prefix="/interviews", tags=["interviews"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

# Namespaces this route's Idempotency-Key cache separately from every other AI route reusing
# app.core.idempotency — see that module's docstring (Phase 9). The third real consumer, after
# "rag_query" (Phase 9) and "learning_roadmap" (Phase 10).
_IDEMPOTENCY_SCOPE = "interview_answer"


def _build_question_read(
    question: InterviewQuestion,
    answer: InterviewAnswer | None,
    evaluation: InterviewEvaluation | None,
) -> InterviewQuestionRead:
    answer_read = None
    if answer is not None:
        evaluation_read = (
            InterviewEvaluationRead.model_validate(evaluation) if evaluation is not None else None
        )
        answer_read = InterviewAnswerRead(
            answer_text=answer.answer_text,
            response_time_seconds=answer.response_time_seconds,
            created_at=answer.created_at,
            evaluation=evaluation_read,
        )
    return InterviewQuestionRead(
        id=question.id,
        question_text=question.question_text,
        category=question.category,
        order_index=question.order_index,
        answer=answer_read,
    )


async def _build_detail(db: AsyncSession, interview: Interview) -> InterviewDetailRead:
    rows = await get_questions_with_details(db, interview_id=interview.id)
    questions = [_build_question_read(q, a, e) for q, a, e in rows]
    return InterviewDetailRead(
        id=interview.id,
        mode=interview.mode,
        target_role=interview.target_role,
        status=interview.status,
        overall_score=float(interview.overall_score)
        if interview.overall_score is not None
        else None,
        created_at=interview.created_at,
        questions=questions,
    )


async def _get_owned_interview_or_404(db: DbDep, interview_id: uuid.UUID, user: User) -> Interview:
    interview = await get_owned_interview(db, interview_id=interview_id, user_id=user.id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")
    return interview


@router.post("", response_model=Envelope[InterviewDetailRead])
async def start_interview(
    request: Request, payload: InterviewCreateRequest, user: UserDep, db: DbDep
) -> Envelope[InterviewDetailRead]:
    """Creates a session + its first question. No LLM call (pure retrieval from the curated
    question bank — app/services/interviews.py::select_next_question), so no Idempotency-Key is
    required — matches `applications.py`'s plain resource-creation-POST precedent, not
    `rag.py`/`learning_roadmap.py`'s AI-cost-controlled POSTs."""
    interview = await create_interview(
        db, user=user, mode=payload.mode, target_role=payload.target_role
    )
    await db.commit()
    data = await _build_detail(db, interview)
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("", response_model=Envelope[list[InterviewRead]])
async def list_interview_history(
    request: Request,
    user: UserDep,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None),
) -> Envelope[list[InterviewRead]]:
    """Cursor-paginated (docs/API.md §1) — a user can start unboundedly many practice sessions,
    unlike `GET /resumes`'s deliberately-unpaginated list."""
    try:
        interviews, next_cursor = await list_interviews(
            db, user_id=user.id, limit=limit, cursor=cursor
        )
    except InvalidCursorError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Envelope(
        data=[InterviewRead.model_validate(i) for i in interviews],
        meta=meta_from_request(request, next_cursor=next_cursor),
    )


@router.get("/analytics", response_model=Envelope[InterviewAnalyticsRead])
async def get_interview_analytics(
    request: Request, user: UserDep, db: DbDep
) -> Envelope[InterviewAnalyticsRead]:
    """Registered before `/{interview_id}` — same route-ordering requirement as `skills.py`'s
    real `/gaps`/`/curated` before `/{id_or_slug}`, otherwise FastAPI would try to parse
    "analytics" as a UUID path param."""
    analytics = await get_analytics(db, user_id=user.id)
    data = InterviewAnalyticsRead(
        total_completed=analytics.total_completed,
        average_overall_score=analytics.average_overall_score,
        average_correctness_score=analytics.average_correctness_score,
        average_depth_score=analytics.average_depth_score,
        average_communication_score=analytics.average_communication_score,
        recent=[
            InterviewAnalyticsRecent(
                interview_id=i.id,
                mode=i.mode,
                overall_score=float(i.overall_score) if i.overall_score is not None else 0.0,
                completed_at=i.updated_at,
            )
            for i in analytics.recent
        ],
    )
    return Envelope(data=data, meta=meta_from_request(request))


@router.get("/{interview_id}", response_model=Envelope[InterviewDetailRead])
async def get_interview(
    request: Request, interview_id: uuid.UUID, user: UserDep, db: DbDep
) -> Envelope[InterviewDetailRead]:
    """Folds the original doc sketch's separate `GET .../evaluation` into this one response —
    every question's answer + evaluation (if submitted) comes back here. The frontend derives
    "the current question" as the first item with `answer is None`."""
    interview = await _get_owned_interview_or_404(db, interview_id, user)
    data = await _build_detail(db, interview)
    return Envelope(data=data, meta=meta_from_request(request))


@router.post("/{interview_id}/answer", response_model=Envelope[InterviewDetailRead])
async def submit_answer(
    request: Request,
    interview_id: uuid.UUID,
    payload: InterviewAnswerRequest,
    user: UserDep,
    db: DbDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[InterviewDetailRead]:
    """The only AI-triggering route in this feature. Idempotency-Key required, real rate-limit
    (reuses app/core/rate_limit.py/idempotency.py verbatim, scope="interview_answer") — same
    control flow as rag.py/learning_roadmap.py (cache check -> rate limit -> reserve -> work ->
    commit -> store), with one deliberate difference from learning_roadmap.py: a genuine
    evaluation failure (`InterviewEvaluationError`) legitimately surfaces as a 502 here, matching
    `rag.py`'s reasoning — there's no deterministic fallback evaluation, the LLM call IS the
    product for this action."""
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key header is required."
        )
    user_id = str(user.id)

    cached = await get_cached_response(_IDEMPOTENCY_SCOPE, user_id, idempotency_key)
    if cached is not None:
        return Envelope(
            data=InterviewDetailRead.model_validate(cached), meta=meta_from_request(request)
        )

    try:
        rate_limit = await check_ai_rate_limit(user_id)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI features are temporarily unavailable. Please try again shortly.",
        ) from exc
    if not rate_limit.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests. Please slow down.",
            headers={"Retry-After": str(max(1, rate_limit.retry_after_seconds))},
        )

    claimed = await reserve(_IDEMPOTENCY_SCOPE, user_id, idempotency_key)
    if not claimed:
        cached = await get_cached_response(_IDEMPOTENCY_SCOPE, user_id, idempotency_key)
        if cached is not None:
            return Envelope(
                data=InterviewDetailRead.model_validate(cached), meta=meta_from_request(request)
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A request with this Idempotency-Key is already being processed.",
        )

    interview = await _get_owned_interview_or_404(db, interview_id, user)
    if interview.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This interview is not in progress."
        )
    question = await get_question_in_interview(
        db, question_id=payload.question_id, interview_id=interview.id
    )
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    if await has_answer(db, question_id=question.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This question has already been answered."
        )

    resume_context = await build_resume_context(db, user_id=user.id)
    try:
        evaluation_result, llm_result = await evaluate_answer(
            mode=interview.mode,
            question_text=question.question_text,
            answer_text=payload.answer_text,
            resume_context=resume_context,
        )
    except InterviewEvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not evaluate this answer: {exc}"
        ) from exc

    try:
        await record_answer(
            db,
            question=question,
            answer_text=payload.answer_text,
            response_time_seconds=payload.response_time_seconds,
            evaluation=evaluation_result,
        )
    except AnswerAlreadySubmittedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    await log_conversation(
        db,
        user_id=user.id,
        feature=AIFeature.INTERVIEW,
        result=llm_result,
        prompt_name="interview_evaluation",
        prompt_version="v1",
    )
    await advance_or_complete(db, interview=interview)
    await db.commit()

    data = await _build_detail(db, interview)
    await store_response(_IDEMPOTENCY_SCOPE, user_id, idempotency_key, data.model_dump(mode="json"))

    return Envelope(data=data, meta=meta_from_request(request))


@router.delete("/{interview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview_session(interview_id: uuid.UUID, user: UserDep, db: DbDep) -> None:
    deleted = await delete_interview(db, user_id=user.id, interview_id=interview_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")
    await db.commit()
