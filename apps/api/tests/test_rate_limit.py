import uuid

import pytest

from app.core.config import settings
from app.core.rate_limit import RateLimitError, check_ai_rate_limit
from app.core.redis import get_redis


class _RaisingRedis:
    def register_script(self, script: str) -> object:
        raise ConnectionError("redis unavailable")


@pytest.fixture
async def rate_limit_user_id() -> str:
    return f"test-user-{uuid.uuid4()}"


@pytest.fixture(autouse=True)
async def _cleanup_bucket(rate_limit_user_id: str):
    yield
    redis = get_redis()
    await redis.delete(f"ratelimit:ai:{rate_limit_user_id}")


async def test_check_ai_rate_limit_allows_up_to_capacity_then_denies(
    monkeypatch: pytest.MonkeyPatch, rate_limit_user_id: str
) -> None:
    monkeypatch.setattr(settings, "rate_limit_ai_per_minute", 3)

    results = [await check_ai_rate_limit(rate_limit_user_id) for _ in range(3)]
    assert all(r.allowed for r in results)

    denied = await check_ai_rate_limit(rate_limit_user_id)
    assert denied.allowed is False
    assert denied.retry_after_seconds > 0


async def test_check_ai_rate_limit_scoped_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_ai_per_minute", 1)
    user_a = f"test-user-a-{uuid.uuid4()}"
    user_b = f"test-user-b-{uuid.uuid4()}"
    try:
        assert (await check_ai_rate_limit(user_a)).allowed is True
        assert (await check_ai_rate_limit(user_a)).allowed is False
        # A different user's bucket is untouched by user_a's usage.
        assert (await check_ai_rate_limit(user_b)).allowed is True
    finally:
        redis = get_redis()
        await redis.delete(f"ratelimit:ai:{user_a}")
        await redis.delete(f"ratelimit:ai:{user_b}")


async def test_check_ai_rate_limit_fails_closed_on_redis_error(
    monkeypatch: pytest.MonkeyPatch, rate_limit_user_id: str
) -> None:
    import app.core.rate_limit as rate_limit_module

    monkeypatch.setattr(rate_limit_module, "get_redis", lambda: _RaisingRedis())

    with pytest.raises(RateLimitError):
        await check_ai_rate_limit(rate_limit_user_id)
