import anyio
import pytest

from app.core.config import Settings
from app.core.exceptions import BadRequestError
from app.infrastructure.cache.no_op_cache import NoOpCache
from app.services.search_service import SearchService


class FakeEmbedder:
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeStore:
    def __init__(self, results):
        self._results = results
        self.calls = 0

    def ensure_ready(self):
        pass

    def count(self):
        return len(self._results)

    def upsert(self, *a):
        return 0

    def search(self, vector, top_k, score_threshold=None):
        self.calls += 1
        return self._results[:top_k]


class RecordingCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def clear(self):
        self.store.clear()


RESULTS = [{"document": "a.pdf", "score": 0.9, "content": "x"}]


def test_search_returns_store_results_on_cache_miss():
    store = FakeStore(RESULTS)
    svc = SearchService(FakeEmbedder(), store, NoOpCache(), Settings())
    assert anyio.run(svc.search, "hello") == RESULTS
    assert store.calls == 1


def test_second_identical_search_is_served_from_cache():
    store = FakeStore(RESULTS)
    svc = SearchService(FakeEmbedder(), store, RecordingCache(), Settings())
    anyio.run(svc.search, "hello")
    anyio.run(svc.search, "hello")
    assert store.calls == 1  # cached the second time


def test_search_rejects_explicit_top_k_above_available():
    store = FakeStore(RESULTS)  # 1 chunk available
    svc = SearchService(FakeEmbedder(), store, NoOpCache(), Settings())
    with pytest.raises(BadRequestError):
        anyio.run(svc.search, "hello", 5)


def test_search_empty_collection_returns_empty():
    svc = SearchService(FakeEmbedder(), FakeStore([]), NoOpCache(), Settings())
    assert anyio.run(svc.search, "hello") == []
