from unittest.mock import MagicMock

from app.core.config import Settings
from app.infrastructure.vector_store.qdrant_store import QdrantVectorStore


def test_ensure_ready_creates_collection_when_missing():
    client = MagicMock()
    client.collection_exists.return_value = False
    QdrantVectorStore(Settings(), client=client).ensure_ready()
    client.create_collection.assert_called_once()


def test_ensure_ready_skips_when_collection_exists():
    client = MagicMock()
    client.collection_exists.return_value = True
    QdrantVectorStore(Settings(), client=client).ensure_ready()
    client.create_collection.assert_not_called()


def test_upsert_replaces_existing_document_then_inserts():
    client = MagicMock()
    store = QdrantVectorStore(Settings(), client=client)
    assert store.upsert("a.pdf", ["c1", "c2"], [[0.1], [0.2]]) == 2
    client.delete.assert_called_once()  # existing chunks for the doc removed first
    client.upsert.assert_called_once()


def test_count_returns_number_of_chunks():
    client = MagicMock()
    client.count.return_value = MagicMock(count=7)
    assert QdrantVectorStore(Settings(), client=client).count() == 7


def test_search_maps_hits_to_dicts():
    client = MagicMock()
    hit = MagicMock(score=0.9, payload={"document": "a.pdf", "content": "x"})
    client.query_points.return_value = MagicMock(points=[hit])
    store = QdrantVectorStore(Settings(), client=client)
    assert store.search([0.1], 5) == [{"document": "a.pdf", "score": 0.9, "content": "x"}]


def test_search_passes_score_threshold():
    client = MagicMock()
    client.query_points.return_value = MagicMock(points=[])
    QdrantVectorStore(Settings(), client=client).search([0.1], 5, 0.2)
    assert client.query_points.call_args.kwargs["score_threshold"] == 0.2
