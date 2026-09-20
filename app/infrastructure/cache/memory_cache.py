"""In-process TTL cache: the 'enable caching without Redis' option.

Bounded in size (LRU eviction) so it can't grow without limit. Suitable for a
single-process deployment; for multiple replicas, swap in a RedisCache behind
the same interface.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

from app.core.config import Settings
from app.infrastructure.cache.cache import Cache


class InMemoryCache(Cache):
    def __init__(self, settings: Settings) -> None:
        self._ttl = settings.cache_ttl_seconds
        self._max_size = settings.cache_max_size
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    async def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return value

    async def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()
