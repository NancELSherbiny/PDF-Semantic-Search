"""Qdrant implementation of the VectorStore interface."""

from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

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
        self._dim = settings.embedding_dim
        self._distance = _DISTANCES.get(settings.distance_metric.lower(), Distance.COSINE)
        # client is injectable so tests can pass a mock instead of a live connection.
        self._client = client or QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    def ensure_ready(self) -> None:
        if not self._client.collection_exists(self._collection):
            logger.info("Creating Qdrant collection '%s' (dim=%d)", self._collection, self._dim)
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._dim, distance=self._distance),
            )

    def upsert(self, document: str, chunks: list[str], vectors: list[list[float]]) -> int:
        # Replace any existing chunks for this document so re-ingesting the same
        # file is idempotent (no duplicate search results).
        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="document", match=MatchValue(value=document))]
            ),
        )
        points = [
            PointStruct(id=str(uuid.uuid4()), vector=v, payload={"document": document, "content": c})
            for c, v in zip(chunks, vectors)
        ]
        self._client.upsert(collection_name=self._collection, points=points)
        logger.info("Upserted %d chunks from '%s' (replaced any existing)", len(points), document)
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
