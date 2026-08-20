from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import settings


@lru_cache
def get_redis() -> Redis:
    """Process-level singleton client for `settings.redis_url` (the app-cache DB — distinct
    from the Celery broker/result-backend DBs, see app/core/config.py). Used by
    `app.services.embeddings` for the embedding cache (docs/AI_ARCHITECTURE.md §5, §7)."""
    return Redis.from_url(settings.redis_url, decode_responses=False)
