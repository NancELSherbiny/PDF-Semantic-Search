from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.infrastructure.vector_store.qdrant_store import QdrantVectorStore


def _existing_collection(client, size):
    client.collection_exists.return_value = True
    client.get_collection.return_value = MagicMock(
        config=MagicMock(params=MagicMock(vectors=MagicMock(size=size)))
    )


def test_ensure_ready_creates_collection_when_missing():
    client = MagicMock()
    client.collection_exists.return_value = False
    QdrantVectorStore(Settings(), client=client).ensure_ready(384)
    client.create_collection.assert_called_once()


def test_ensure_ready_ok_when_dimension_matches():
    client = MagicMock()
    _existing_collection(client, 384)
    QdrantVectorStore(Settings(), client=client).ensure_ready(384)
    client.create_collection.assert_not_called()


def test_ensure_ready_raises_on_dimension_mismatch():
    client = MagicMock()
    _existing_collection(client, 768)
    with pytest.raises(RuntimeError):
        QdrantVectorStore(Settings(), client=client).ensure_ready(384)


def test_upsert_returns_chunk_count():
    client = MagicMock()
    store = QdrantVectorStore(Settings(), client=client)
    assert store.upsert("a.pdf", ["c1", "c2"], [[0.1], [0.2]]) == 2
    client.upsert.assert_called_once()


def test_upsert_uses_deterministic_ids_for_same_document():
    client = MagicMock()
    store = QdrantVectorStore(Settings(), client=client)
    store.upsert("a.pdf", ["c1", "c2"], [[0.1], [0.2]])
    ids1 = [p.id for p in client.upsert.call_args.kwargs["points"]]
    store.upsert("a.pdf", ["c1", "c2"], [[0.1], [0.2]])
    ids2 = [p.id for p in client.upsert.call_args.kwargs["points"]]
    assert ids1 == ids2         # re-ingest overwrites the same points (no duplicates)
    assert len(set(ids1)) == 2  # one distinct id per chunk index


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
