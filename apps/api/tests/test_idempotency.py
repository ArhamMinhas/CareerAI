import uuid

import pytest

from app.core.idempotency import get_cached_response, reserve, store_response
from app.core.redis import get_redis

_SCOPE = "test_scope"


class _RaisingRedis:
    async def get(self, key: str) -> None:
        raise ConnectionError("redis unavailable")

    async def set(self, *args: object, **kwargs: object) -> None:
        raise ConnectionError("redis unavailable")


@pytest.fixture
async def idempotency_ids() -> tuple[str, str]:
    return f"test-user-{uuid.uuid4()}", f"test-key-{uuid.uuid4()}"


@pytest.fixture(autouse=True)
async def _cleanup_idempotency_key(idempotency_ids: tuple[str, str]):
    user_id, key = idempotency_ids
    yield
    redis = get_redis()
    await redis.delete(f"idempotency:{_SCOPE}:{user_id}:{key}")


async def test_get_cached_response_is_none_for_unseen_key(idempotency_ids: tuple[str, str]) -> None:
    user_id, key = idempotency_ids
    assert await get_cached_response(_SCOPE, user_id, key) is None


async def test_reserve_claims_first_and_rejects_second(idempotency_ids: tuple[str, str]) -> None:
    user_id, key = idempotency_ids
    assert await reserve(_SCOPE, user_id, key) is True
    assert await reserve(_SCOPE, user_id, key) is False


async def test_get_cached_response_is_none_while_reservation_is_in_progress(
    idempotency_ids: tuple[str, str],
) -> None:
    user_id, key = idempotency_ids
    await reserve(_SCOPE, user_id, key)
    assert await get_cached_response(_SCOPE, user_id, key) is None


async def test_store_response_then_get_cached_response_round_trips(
    idempotency_ids: tuple[str, str],
) -> None:
    user_id, key = idempotency_ids
    await reserve(_SCOPE, user_id, key)
    await store_response(_SCOPE, user_id, key, {"answer": "42", "citations": []})

    cached = await get_cached_response(_SCOPE, user_id, key)
    assert cached == {"answer": "42", "citations": []}


async def test_reserve_scoped_per_user_not_globally_per_key(
    idempotency_ids: tuple[str, str],
) -> None:
    _, key = idempotency_ids
    user_a = f"test-user-a-{uuid.uuid4()}"
    user_b = f"test-user-b-{uuid.uuid4()}"
    try:
        assert await reserve(_SCOPE, user_a, key) is True
        # Same literal key, different user — must not collide.
        assert await reserve(_SCOPE, user_b, key) is True
    finally:
        redis = get_redis()
        await redis.delete(f"idempotency:{_SCOPE}:{user_a}:{key}")
        await redis.delete(f"idempotency:{_SCOPE}:{user_b}:{key}")


async def test_reserve_scoped_per_caller_not_globally_per_user_and_key(
    idempotency_ids: tuple[str, str],
) -> None:
    """Two different routes/features reusing this module with the same (user, key) pair — e.g.
    a client accidentally reusing an Idempotency-Key value across two different endpoints — must
    not replay one endpoint's cached response as if it were the other's."""
    user_id, key = idempotency_ids
    other_scope = "other_test_scope"
    try:
        await reserve(_SCOPE, user_id, key)
        await store_response(_SCOPE, user_id, key, {"from": _SCOPE})

        # A different scope with the identical (user, key) pair sees no cached response at all.
        assert await get_cached_response(other_scope, user_id, key) is None
        assert await reserve(other_scope, user_id, key) is True
    finally:
        redis = get_redis()
        await redis.delete(f"idempotency:{other_scope}:{user_id}:{key}")


async def test_get_cached_response_fails_open_on_redis_error(
    monkeypatch: pytest.MonkeyPatch, idempotency_ids: tuple[str, str]
) -> None:
    import app.core.idempotency as idempotency_module

    monkeypatch.setattr(idempotency_module, "get_redis", lambda: _RaisingRedis())
    user_id, key = idempotency_ids
    assert await get_cached_response(_SCOPE, user_id, key) is None


async def test_reserve_fails_open_on_redis_error(
    monkeypatch: pytest.MonkeyPatch, idempotency_ids: tuple[str, str]
) -> None:
    import app.core.idempotency as idempotency_module

    monkeypatch.setattr(idempotency_module, "get_redis", lambda: _RaisingRedis())
    user_id, key = idempotency_ids
    assert await reserve(_SCOPE, user_id, key) is True
