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


def _ingest(service, documents):
    return anyio.run(service.ingest_documents, documents)


def test_single_document_is_indexed():
    store = FakeStore()
    assert _ingest(_service(store, FakeCache()), [("a.pdf", b"hello world foo")]) == ["a.pdf"]
    assert store.upserts == [("a.pdf", 3)]


def test_ingest_empty_document_is_rejected():
    store = FakeStore()
    with pytest.raises(BadRequestError):
        _ingest(_service(store, FakeCache()), [("empty.pdf", b"")])
    assert store.upserts == []


def test_one_invalid_document_means_nothing_is_indexed():
    store, cache = FakeStore(), FakeCache()
    with pytest.raises(BadRequestError):
        _ingest(_service(store, cache), [("good.pdf", b"hello world"), ("empty.pdf", b"")])
    assert store.upserts == []  # good.pdf must NOT have been indexed
    assert cache.cleared == 0   # nothing changed, so the cache is left alone


def test_all_valid_documents_are_indexed():
    store, cache = FakeStore(), FakeCache()
    files = _ingest(_service(store, cache), [("good.pdf", b"hello world"), ("good2.pdf", b"more text here")])
    assert files == ["good.pdf", "good2.pdf"]
    assert store.upserts == [("good.pdf", 2), ("good2.pdf", 3)]
    assert cache.cleared == 1
