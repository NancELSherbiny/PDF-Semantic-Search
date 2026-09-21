"""
Centralized application configuration.

Every operational parameter lives here and is overridable via environment
variables, so no other module reads os.environ directly. Access it through
`get_settings()`, which builds a single cached instance for the process.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API
    api_title: str = "PDF Ingestor & Semantic Search API"
    api_version: str = "1.0.0"
    log_level: str = "INFO"

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    normalize_embeddings: bool = True

    # Chunking
    chunk_size: int = 180
    chunk_overlap: int = 30

    # Ingestion
    ingest_base_dir: str = "/data"  # directory-path ingestion is restricted to this base

    # Vector store (Qdrant)
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "pdf_chunks"
    distance_metric: str = "cosine"  # cosine | dot | euclidean

    # Search
    top_k: int = 5
    score_threshold: float = 0.0  # minimum cosine score; 0.0 drops unrelated/negative-score chunks

    # Cache — disabled by default; enable later without touching business logic.
    cache_enabled: bool = False
    cache_backend: str = "memory"  # memory (RedisCache can be added behind the same interface)
    cache_ttl_seconds: int = 300
    cache_max_size: int = 1024


@lru_cache
def get_settings() -> Settings:
    """Return the singleton Settings, built once from the environment."""
    return Settings()
