import uuid

import pytest

import app.services.embeddings as embeddings_module
from app.core.db import AsyncSessionLocal
from app.models.embedding import Embedding
from app.services.embeddings import _cache_key, embed_text, store_embedding


class _FakeProvider:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.calls = 0
        self._vector = vector or [0.1, 0.2, 0.3]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [self._vector for _ in texts]


class _RaisingRedis:
    async def get(self, key: str) -> None:
        raise ConnectionError("redis unavailable")

    async def set(self, *args: object, **kwargs: object) -> None:
        raise ConnectionError("redis unavailable")


@pytest.fixture
async def _cleanup_cache_key():
    keys: list[str] = []
    yield keys
    redis = embeddings_module.get_redis()
    for key in keys:
        await redis.delete(key)


async def test_embed_text_caches_by_content_hash(
    monkeypatch: pytest.MonkeyPatch, _cleanup_cache_key: list[str]
) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(embeddings_module, "get_provider", lambda: provider)
    text = f"unique resume text {uuid.uuid4()}"
    _cleanup_cache_key.append(_cache_key(text, embeddings_module.settings.embedding_model))

    first = await embed_text(text)
    second = await embed_text(text)

    assert first == second == [0.1, 0.2, 0.3]
    assert provider.calls == 1  # second call hit the cache, not the provider


async def test_embed_text_survives_cache_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(embeddings_module, "get_provider", lambda: provider)
    monkeypatch.setattr(embeddings_module, "get_redis", lambda: _RaisingRedis())

    vector = await embed_text(f"text {uuid.uuid4()}")

    assert vector == [0.1, 0.2, 0.3]
    assert provider.calls == 1


async def test_store_embedding_persists_row(
    monkeypatch: pytest.MonkeyPatch, _cleanup_cache_key: list[str]
) -> None:
    provider = _FakeProvider(vector=[0.1] * 1536)  # must match `EMBEDDING_DIMENSIONS`
    monkeypatch.setattr(embeddings_module, "get_provider", lambda: provider)
    text = f"resume text {uuid.uuid4()}"
    _cleanup_cache_key.append(_cache_key(text, embeddings_module.settings.embedding_model))
    owner_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        embedding = await store_embedding(db, owner_type="resume", owner_id=owner_id, text=text)
        await db.commit()
        embedding_id = embedding.id

    async with AsyncSessionLocal() as db:
        row = await db.get(Embedding, embedding_id)
        assert row is not None
        assert row.owner_type == "resume"
        assert row.owner_id == owner_id
        assert row.model == embeddings_module.settings.embedding_model
        assert len(row.embedding) == 1536

        await db.delete(row)
        await db.commit()
