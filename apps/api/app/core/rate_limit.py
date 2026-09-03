import logging
from dataclasses import dataclass

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "ratelimit:ai"
# A couple minutes of inactivity fully refills any bucket size this app will realistically use
# (`rate_limit_ai_per_minute` is a small int) — this only bounds idle-key growth in Redis, not
# the actual rate-limiting behavior, which is entirely governed by the token math below.
_BUCKET_TTL_SECONDS = 120

# Executed atomically via `EVAL` — a single round trip, so concurrent requests from the same user
# can't race a separate GET-then-SET the way a naive Python read-modify-write would. Reads the
# time from Redis itself (`TIME`), not the caller's clock, so this stays correct across multiple
# app instances with any amount of clock drift between them.
_TOKEN_BUCKET_SCRIPT = """
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])

local time_parts = redis.call("TIME")
local now = tonumber(time_parts[1]) + tonumber(time_parts[2]) / 1000000

local data = redis.call("HMGET", KEYS[1], "tokens", "updated_at")
local tokens = tonumber(data[1])
local updated_at = tonumber(data[2])

if tokens == nil then
    tokens = capacity
    updated_at = now
end

local elapsed = now - updated_at
if elapsed < 0 then
    elapsed = 0
end
tokens = math.min(capacity, tokens + elapsed * refill_rate)

local allowed = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
end

redis.call("HSET", KEYS[1], "tokens", tostring(tokens), "updated_at", tostring(now))
redis.call("EXPIRE", KEYS[1], ttl)

local retry_after = 0
if allowed == 0 then
    retry_after = math.ceil((1 - tokens) / refill_rate)
end

return {allowed, retry_after}
"""


class RateLimitError(Exception):
    """Raised when the limiter itself can't be evaluated (e.g. Redis unavailable). The AI rate
    limiter fails *closed* — deliberately the opposite of `app.services.embeddings`'s cache,
    which fails open because it's a cost optimization, not a correctness dependency. A rate
    limiter's entire purpose is bounding cost/abuse, so silently letting every request through
    on a Redis outage would defeat the reason it exists."""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


async def check_ai_rate_limit(user_id: str) -> RateLimitResult:
    """Token-bucket per user (docs/API.md §4), keyed on `user_id` and scoped to this one prefix
    — not shared with `rate_limit_default_per_minute`'s general-API limiter, which doesn't exist
    yet (this is the first real rate-limiter implementation in the codebase; see
    `app/api/v1/rag.py`'s docstring for why it's scoped to just the RAG query route for now).
    Capacity and refill rate both derive from `settings.rate_limit_ai_per_minute` — a bucket
    that holds `N` tokens and refills continuously at `N` tokens/minute, so a user can burst up
    to `N` requests immediately and then sustain `N`/minute indefinitely, rather than a harder
    fixed-window reset."""
    redis = get_redis()
    capacity = settings.rate_limit_ai_per_minute
    refill_rate_per_second = capacity / 60.0
    key = f"{_KEY_PREFIX}:{user_id}"

    try:
        # `register_script` (not a raw `EVAL` call) so redis-py transparently uses `EVALSHA` with
        # a `NOSCRIPT`-triggered fallback re-`EVAL` — avoids re-sending the script body on every
        # request, and sidesteps a redis-py stub typing quirk where `Redis.eval`'s sync/async
        # overloads don't resolve cleanly under mypy.
        script = redis.register_script(_TOKEN_BUCKET_SCRIPT)
        allowed, retry_after = await script(
            keys=[key], args=[str(capacity), str(refill_rate_per_second), str(_BUCKET_TTL_SECONDS)]
        )
    except Exception as exc:
        logger.warning("AI rate limiter unavailable; failing closed.", exc_info=True)
        raise RateLimitError("Rate limiter is temporarily unavailable.") from exc

    return RateLimitResult(allowed=bool(int(allowed)), retry_after_seconds=int(retry_after))
