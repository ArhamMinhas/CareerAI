from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag_answer import RagAnswerError, answer_question
from app.core.db import get_db
from app.core.idempotency import get_cached_response, reserve, store_response
from app.core.rate_limit import RateLimitError, check_ai_rate_limit
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.envelope import Envelope, meta_from_request
from app.schemas.rag import RagQueryRequest, RagQueryResponse
from app.services.ai_conversations import AIFeature, log_conversation

router = APIRouter(prefix="/rag", tags=["rag"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

# Namespaces this route's Idempotency-Key cache separately from any future second caller of
# app.core.idempotency — see that module's docstring.
_IDEMPOTENCY_SCOPE = "rag_query"


@router.post("/query", response_model=Envelope[RagQueryResponse])
async def query_rag(
    request: Request,
    payload: RagQueryRequest,
    user: UserDep,
    db: DbDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Envelope[RagQueryResponse]:
    """Grounded question-answering over the curated `resources` knowledge base
    (docs/AI_ARCHITECTURE.md §6, Phase 9) — backs `/dashboard/ask`. The only AI-triggering route
    in the codebase with a *real* rate limiter and a *real* Idempotency-Key dedup so far (every
    other AI route, e.g. `/resumes/{id}/analyze`, only checks the header is present) — this is
    the first genuinely unbounded-per-request-cost route, and building both controls for real
    here rather than deferring them again matches this phase's "no shortcuts" mandate. Not
    retrofitted onto other existing AI routes: real, valuable follow-up work, but a separate,
    broader change outside this phase's scope.
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key header is required."
        )
    user_id = str(user.id)

    # A previously-completed response for this key always replays first, regardless of rate
    # limit state — a client retrying a call it already paid for shouldn't be rate-limited by
    # its own retry.
    cached = await get_cached_response(_IDEMPOTENCY_SCOPE, user_id, idempotency_key)
    if cached is not None:
        return Envelope(
            data=RagQueryResponse.model_validate(cached), meta=meta_from_request(request)
        )

    # Rate limit is checked *before* reserving the idempotency key: reserving first would consume
    # the client's retry slot even when this attempt never runs the real work, and a client that
    # retries after the rate limit clears would then find its own key already (wrongly) claimed.
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
                data=RagQueryResponse.model_validate(cached), meta=meta_from_request(request)
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A request with this Idempotency-Key is already being processed.",
        )

    try:
        answer, citations, result = await answer_question(db, payload.question)
    except RagAnswerError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not generate an answer: {exc}"
        ) from exc

    await log_conversation(
        db,
        user_id=user.id,
        feature=AIFeature.RAG_CHAT,
        result=result,
        prompt_name="rag_answer",
        prompt_version="v1",
    )
    await db.commit()

    response = RagQueryResponse(answer=answer, citations=citations)
    await store_response(
        _IDEMPOTENCY_SCOPE, user_id, idempotency_key, response.model_dump(mode="json")
    )

    return Envelope(data=response, meta=meta_from_request(request))
