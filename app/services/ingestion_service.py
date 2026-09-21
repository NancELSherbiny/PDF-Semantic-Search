"""
Ingestion orchestration: document -> extract -> chunk -> embed -> store.

Knows the pipeline order, not the low-level details of PDF parsing, the model,
or Qdrant — those live behind the injected collaborators.
"""

from __future__ import annotations

import anyio

from app.core.exceptions import BadRequestError
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

    def _prepare(self, filename: str, data: bytes) -> list[str]:
        """Extract and chunk one document, rejecting it if it has no usable text.
        Writes nothing."""
        chunks = self._chunker.chunk(self._extractor.extract(data))
        if not chunks:
            logger.warning("Rejected '%s': no extractable text", filename)
            raise BadRequestError(f"No extractable text found in '{filename}'.")
        return chunks

    def _index(self, prepared: list[tuple[str, list[str]]]) -> None:
        # Embed everything before the first write, so a model failure can't leave
        # the request half-indexed.
        embedded = [(name, chunks, self._embedder.embed(chunks)) for name, chunks in prepared]
        for name, chunks, vectors in embedded:
            self._store.upsert(name, chunks, vectors)
            logger.info("Ingested '%s' -> %d chunks", name, len(chunks))

    async def ingest_documents(self, documents: list[tuple[str, bytes]]) -> list[str]:
        """
        All-or-nothing per request: every document is extracted and validated
        before anything is written, so one bad file means nothing from the
        request is indexed. Blocking work runs off the event loop.
        """
        logger.info("Ingestion started: %d document(s)", len(documents))
        prepared: list[tuple[str, list[str]]] = []
        for filename, data in documents:
            chunks = await anyio.to_thread.run_sync(self._prepare, filename, data)
            prepared.append((filename, chunks))

        await anyio.to_thread.run_sync(self._index, prepared)
        await self._cache.clear()  # only after a successful index
        logger.info("Ingestion completed: %d document(s)", len(prepared))
        return [filename for filename, _ in prepared]
