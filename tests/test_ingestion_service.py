import anyio
import pytest

from app.core.exceptions import BadRequestError
from app.services.ingestion_service import IngestionService


class FakeExtractor:
    def extract(self, data):
        return data.decode("utf-8", "ignore")


class FakeChunker:
    def chunk(self, text):
        return text.split()


class FakeEmbedder:
    def embed(self, texts):
        return [[1.0] for _ in texts]


class FakeStore:
    def __init__(self):
        self.upserts = []

    def ensure_ready(self):
        pass

    def upsert(self, document, chunks, vectors):
        self.upserts.append((document, len(chunks)))
        return len(chunks)

    def search(self, *a):
        return []


class FakeCache:
    def __init__(self):
        self.cleared = 0

    async def get(self, key):
        return None

    async def set(self, key, value):
        pass

    async def delete(self, key):
        pass

    async def clear(self):
        self.cleared += 1


def _service(store, cache):
    return IngestionService(FakeExtractor(), FakeChunker(), FakeEmbedder(), store, cache)


def test_ingest_document_returns_chunk_count():
    store = FakeStore()
    assert _service(store, FakeCache()).ingest_document("a.pdf", b"hello world foo") == 3
    assert store.upserts == [("a.pdf", 3)]


def test_ingest_empty_document_is_rejected():
    store = FakeStore()
    with pytest.raises(BadRequestError):
        _service(store, FakeCache()).ingest_document("empty.pdf", b"")
    assert store.upserts == []


def test_ingest_documents_invalidates_cache():
    cache = FakeCache()
    files = anyio.run(_service(FakeStore(), cache).ingest_documents, [("a.pdf", b"hello world")])
    assert files == ["a.pdf"]
    assert cache.cleared == 1
