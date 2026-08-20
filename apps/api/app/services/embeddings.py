import hashlib
import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.router import get_provider
from app.core.config import settings
from app.core.redis import get_redis
from app.models.embedding import Embedding

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days
_CACHE_PREFIX = "embedding"


def _cache_key(text: str, model: str) -> str:
    # Content-hash cache key (docs/AI_ARCHITECTURE.md §5, §7) — re-embedding identical text
    # under the same model always hits the same key, regardless of which owner it's for.
    digest = hashlib.sha256(f"{model}:{text}".encode()).hexdigest()
    return f"{_CACHE_PREFIX}:{digest}"


async def embed_text(text: str) -> list[float]:
    """Embeds a single string via the active provider's `embed()`, through a Redis
    content-hash cache so re-embedding identical content (e.g. re-uploading an unchanged
    resume) never makes a second provider call. A cache read/write failure degrades to calling
    the provider directly rather than blocking the caller — the cache is a cost optimization,
    not a correctness dependency, so Redis being briefly unavailable shouldn't fail an upload.
    """
    model = settings.embedding_model
    key = _cache_key(text, model)
    redis = get_redis()

    try:
        cached = await redis.get(key)
    except Exception:
        logger.warning("Embedding cache read failed; calling provider directly.", exc_info=True)
        cached = None
    if cached is not None:
        return json.loads(cached)

    provider = get_provider()
    vector = (await provider.embed([text]))[0]

    try:
        await redis.set(key, json.dumps(vector), ex=_CACHE_TTL_SECONDS)
    except Exception:
        logger.warning("Embedding cache write failed; continuing without caching.", exc_info=True)

    return vector


async def store_embedding(
    db: AsyncSession, *, owner_type: str, owner_id: uuid.UUID, text: str
) -> Embedding:
    """Embeds `text` and persists the durable copy in `embeddings` (docs/DATABASE.md §2.2) —
    the row pgvector similarity search reads from. Always inserts a new row rather than
    updating an existing one for this owner: an embedding is a snapshot of specific content, and
    keeping history (e.g. across resume re-analyses) is cheap and lets a caller compare over
    time; readers pick the most recent by `created_at`. Does not commit — same convention as
    `app.services.ai_conversations.log_conversation`, so callers control the transaction.
    """
    vector = await embed_text(text)
    embedding = Embedding(
        owner_type=owner_type,
        owner_id=owner_id,
        embedding=vector,
        model=settings.embedding_model,
    )
    db.add(embedding)
    await db.flush()
    return embedding
