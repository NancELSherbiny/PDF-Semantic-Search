"""
Ingestion orchestration: document -> extract -> chunk -> embed -> store.

Knows the pipeline order, not the low-level details of PDF parsing, the model,
or Qdrant — those live behind the injected collaborators.
"""

from __future__ import annotations

import anyio

from app.core.logging import get_logger
from app.infrastructure.cache.cache import Cache
from app.infrastructure.vector_store.base import VectorStore
from app.services.chunking_service import ChunkingService
from app.services.document_extractor import DocumentExtractor
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)


class IngestionService:
    def __init__(
        self,
        extractor: DocumentExtractor,
        chunker: ChunkingService,
        embedder: EmbeddingService,
        vector_store: VectorStore,
        cache: Cache,
    ) -> None:
        self._extractor = extractor
        self._chunker = chunker
        self._embedder = embedder
        self._store = vector_store
        self._cache = cache

    def ingest_document(self, filename: str, data: bytes) -> int:
        """Run the pipeline for one document. Blocking; called via a worker thread."""
        text = self._extractor.extract(data)
        chunks = self._chunker.chunk(text)
        if not chunks:
            logger.warning("No text extracted from '%s'; nothing to index", filename)
            return 0
        vectors = self._embedder.embed(chunks)
        self._store.upsert(filename, chunks, vectors)
        logger.info("Ingested '%s' -> %d chunks", filename, len(chunks))
        return len(chunks)

    async def ingest_documents(self, documents: list[tuple[str, bytes]]) -> list[str]:
        """Ingest documents off the event loop, then invalidate the search cache."""
        logger.info("Ingestion started: %d document(s)", len(documents))
        processed: list[str] = []
        for filename, data in documents:
            await anyio.to_thread.run_sync(self.ingest_document, filename, data)
            processed.append(filename)
        await self._cache.clear()  # new documents can change search results
        logger.info("Ingestion completed: %d document(s)", len(processed))
        return processed
