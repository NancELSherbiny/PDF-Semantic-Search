"""
Search orchestration: query -> (cache) -> embed -> vector search -> results.

Depends on the Cache interface, not any specific cache. With the default
NoOpCache every lookup misses, so behavior is identical to "no caching".
"""

from __future__ import annotations

import hashlib

import anyio

from app.core.config import Settings
from app.core.exceptions import BadRequestError
from app.core.logging import get_logger
from app.infrastructure.cache.cache import Cache
from app.infrastructure.vector_store.base import VectorStore
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)


class SearchService:
    def __init__(
        self,
        embedder: EmbeddingService,
        vector_store: VectorStore,
        cache: Cache,
        settings: Settings,
    ) -> None:
        self._embedder = embedder
        self._store = vector_store
        self._cache = cache
        self._default_top_k = settings.top_k
        self._score_threshold = settings.score_threshold

    async def search(self, query: str, top_k: int | None = None) -> list[dict]:
        available = await anyio.to_thread.run_sync(self._store.count)
        # Reject only an explicit top_k that exceeds what's stored; an omitted
        # top_k falls back to the default and returns whatever is available.
        if top_k is not None and top_k > available:
            raise BadRequestError(
                f"top_k ({top_k}) exceeds the number of available chunks ({available})."
            )
        if available == 0:
            return []

        effective_top_k = top_k or self._default_top_k
        key = self._cache_key(query, effective_top_k)

        cached = await self._cache.get(key)
        if cached is not None:
            logger.info("Cache hit (top_k=%d)", effective_top_k)
            return cached
        logger.info("Cache miss; running search (top_k=%d)", effective_top_k)

        vectors = await anyio.to_thread.run_sync(self._embedder.embed, [query])
        results = await anyio.to_thread.run_sync(
            self._store.search, vectors[0], effective_top_k, self._score_threshold
        )
        await self._cache.set(key, results)
        return results

    @staticmethod
    def _cache_key(query: str, top_k: int) -> str:
        digest = hashlib.sha256(f"{query.strip().lower()}::{top_k}".encode()).hexdigest()[:16]
        return f"search:{digest}"
