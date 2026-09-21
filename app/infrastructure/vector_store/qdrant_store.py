"""Qdrant implementation of the VectorStore interface."""

from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.vector_store.base import VectorStore

logger = get_logger(__name__)

_DISTANCES = {
    "cosine": Distance.COSINE,
    "dot": Distance.DOT,
    "euclidean": Distance.EUCLID,
}


class QdrantVectorStore(VectorStore):
    def __init__(self, settings: Settings, client: QdrantClient | None = None) -> None:
        self._collection = settings.qdrant_collection
        self._distance = _DISTANCES.get(settings.distance_metric.lower(), Distance.COSINE)
        # client is injectable so tests can pass a mock instead of a live connection.
        self._client = client or QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    def ensure_ready(self, dimension: int) -> None:
        if self._client.collection_exists(self._collection):
            existing = self._client.get_collection(self._collection).config.params.vectors.size
            if existing != dimension:
                raise RuntimeError(
                    f"Collection '{self._collection}' has vector dimension {existing}, "
                    f"but the embedding model produces {dimension}."
                )
            return
        logger.info("Creating Qdrant collection '%s' (dim=%d)", self._collection, dimension)
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=dimension, distance=self._distance),
        )

    def upsert(self, document: str, chunks: list[str], vectors: list[list[float]]) -> int:
        # Deterministic IDs (document + chunk index) make re-ingesting the same
        # document overwrite the same points instead of duplicating — which also
        # removes the delete-then-insert race under concurrent same-doc ingestion.
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document}:{i}")),
                vector=v,
                payload={"document": document, "content": c},
            )
            for i, (c, v) in enumerate(zip(chunks, vectors))
        ]
        self._client.upsert(collection_name=self._collection, points=points)
        logger.info("Upserted %d chunks from '%s'", len(points), document)
        return len(points)

    def count(self) -> int:
        return self._client.count(collection_name=self._collection, exact=True).count

    def search(
        self, vector: list[float], top_k: int, score_threshold: float | None = None
    ) -> list[dict]:
        response = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            {
                "document": hit.payload.get("document", ""),
                "score": hit.score,
                "content": hit.payload.get("content", ""),
            }
            for hit in response.points
        ]
