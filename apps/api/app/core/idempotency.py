import json
import logging
from typing import Any

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "idempotency"
_RESPONSE_TTL_SECONDS = 60 * 60 * 24  # 24h — how long a completed response is replayed
# Deliberately much shorter than `_RESPONSE_TTL_SECONDS`: this only needs to outlive a single
# in-flight request. Using the 24h TTL here too would mean any request that fails *after*
# `reserve()` but *before* `store_response()` (a raised `RagAnswerError`, a crash, a pod restart)
# leaves the key wedged at "in progress" for a full day, permanently 409-ing every retry with
# that same key. A short TTL self-heals: a stuck reservation simply expires and the next retry
# reserves cleanly, with no explicit rollback needed on every possible failure path.
_RESERVATION_TTL_SECONDS = 120
_IN_PROGRESS_SENTINEL = b"__IN_PROGRESS__"


def _key(scope: str, user_id: str, idempotency_key: str) -> str:
    # `scope` (a short, fixed string identifying the calling route/feature — e.g. "rag_query")
    # namespaces the key so two different endpoints can't collide on the same client-supplied
    # Idempotency-Key value for the same user and accidentally replay each other's cached
    # response. Required, not optional, so a future second caller of this module can't forget
    # it — this module is generic infrastructure, not written for a single route.
    return f"{_KEY_PREFIX}:{scope}:{user_id}:{idempotency_key}"


async def get_cached_response(
    scope: str, user_id: str, idempotency_key: str
) -> dict[str, Any] | None:
    """Returns the previously-completed response body for this (scope, user, key) triple, or
    `None` if it hasn't been seen yet, or is currently in flight (see `reserve`). A cache read
    failure degrades to `None` — treat the key as unseen — rather than blocking the request:
    unlike the rate limiter, a missed dedup only risks one duplicate LLM call, not unbounded
    cost, so this stays fail-open, same as the embedding cache in `app.services.embeddings`."""
    redis = get_redis()
    try:
        raw = await redis.get(_key(scope, user_id, idempotency_key))
    except Exception:
        logger.warning("Idempotency cache read failed; treating key as unseen.", exc_info=True)
        return None
    if raw is None or raw == _IN_PROGRESS_SENTINEL:
        return None
    result: dict[str, Any] = json.loads(raw)
    return result


async def reserve(scope: str, user_id: str, idempotency_key: str) -> bool:
    """Atomically claims this (scope, user, key) triple for the *current* request via
    `SET ... NX`. Returns `True` if this request is the first to claim it (the caller should
    proceed with the real work), or `False` if another request already claimed it — either it's
    still in flight, or it already finished and cached its response (the caller should re-check
    `get_cached_response` before treating this as a conflict). A reservation failure (Redis
    down) degrades to "proceed" rather than blocking the request — same fail-open reasoning as
    `get_cached_response`."""
    redis = get_redis()
    try:
        claimed = await redis.set(
            _key(scope, user_id, idempotency_key),
            _IN_PROGRESS_SENTINEL,
            nx=True,
            ex=_RESERVATION_TTL_SECONDS,
        )
    except Exception:
        logger.warning("Idempotency reservation failed; proceeding without dedup.", exc_info=True)
        return True
    return bool(claimed)


async def store_response(
    scope: str, user_id: str, idempotency_key: str, response_body: dict[str, Any]
) -> None:
    redis = get_redis()
    try:
        await redis.set(
            _key(scope, user_id, idempotency_key),
            json.dumps(response_body),
            ex=_RESPONSE_TTL_SECONDS,
        )
    except Exception:
        logger.warning("Idempotency response cache write failed.", exc_info=True)
