"""
Application entrypoint: builds the FastAPI app and wires its dependencies.

Expensive resources (the embedding model, the Qdrant client) are created once in
the lifespan and shared via app.state, so requests reuse them instead of
rebuilding them each time.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI

from app.api.routes import health, ingest, search
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.infrastructure.cache.cache import Cache
from app.infrastructure.cache.memory_cache import InMemoryCache
from app.infrastructure.cache.no_op_cache import NoOpCache
from app.infrastructure.vector_store.qdrant_store import QdrantVectorStore
from app.services.chunking_service import ChunkingService
from app.services.document_extractor import DocumentExtractor
from app.services.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.search_service import SearchService

logger = get_logger(__name__)


def _build_cache(settings: Settings) -> Cache:
    if settings.cache_enabled and settings.cache_backend == "memory":
        logger.info("Cache enabled: in-memory")
        return InMemoryCache(settings)
    logger.info("Cache disabled (NoOpCache)")
    return NoOpCache()


async def _wait_for_vector_store(store: QdrantVectorStore, retries: int = 20, delay: float = 1.0) -> None:
    # The DB container may still be booting when the app starts; retry briefly.
    for attempt in range(1, retries + 1):
        try:
            store.ensure_ready()
            return
        except Exception as exc:
            logger.warning("Vector store not ready (attempt %d/%d): %s", attempt, retries, exc)
            await anyio.sleep(delay)
    raise RuntimeError("Vector store did not become ready in time")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    logger.info("Starting up")

    extractor = DocumentExtractor()
    chunker = ChunkingService(settings)
    embedder = EmbeddingService(settings)  # loads the model once
    vector_store = QdrantVectorStore(settings)
    await _wait_for_vector_store(vector_store)
    cache = _build_cache(settings)

    app.state.ingestion_service = IngestionService(extractor, chunker, embedder, vector_store, cache)
    app.state.search_service = SearchService(embedder, vector_store, cache, settings)
    logger.info("Startup complete")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    app = FastAPI(title=settings.api_title, version=settings.api_version, lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(search.router)
    return app


app = create_app()
