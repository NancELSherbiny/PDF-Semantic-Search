import anyio

import app.infrastructure.cache.memory_cache as memory_cache
from app.core.config import Settings
from app.infrastructure.cache.memory_cache import InMemoryCache
from app.infrastructure.cache.no_op_cache import NoOpCache


def test_noop_cache_never_stores():
    c = NoOpCache()
    anyio.run(c.set, "k", "v")
    assert anyio.run(c.get, "k") is None


def test_memory_cache_set_and_get():
    c = InMemoryCache(Settings(cache_ttl_seconds=100, cache_max_size=10))
    anyio.run(c.set, "k", [1, 2, 3])
    assert anyio.run(c.get, "k") == [1, 2, 3]


def test_memory_cache_expires_after_ttl(monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(memory_cache.time, "monotonic", lambda: clock["t"])
    c = InMemoryCache(Settings(cache_ttl_seconds=5, cache_max_size=10))
    anyio.run(c.set, "k", "v")
    clock["t"] += 10
    assert anyio.run(c.get, "k") is None


def test_memory_cache_evicts_oldest_over_max_size():
    c = InMemoryCache(Settings(cache_ttl_seconds=100, cache_max_size=2))
    anyio.run(c.set, "a", 1)
    anyio.run(c.set, "b", 2)
    anyio.run(c.set, "c", 3)
    assert anyio.run(c.get, "a") is None
    assert anyio.run(c.get, "c") == 3


def test_memory_cache_clear():
    c = InMemoryCache(Settings(cache_ttl_seconds=100, cache_max_size=10))
    anyio.run(c.set, "k", "v")
    anyio.run(c.clear)
    assert anyio.run(c.get, "k") is None
