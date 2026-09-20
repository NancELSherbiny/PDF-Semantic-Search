"""
Cache interface.

Async so an async backend (e.g. Redis) can be dropped in later without changing
SearchService. `clear()` exists for invalidation: ingestion can change search
results, so the cache is cleared after new documents are added.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Cache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any | None: ...

    @abstractmethod
    async def set(self, key: str, value: Any) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def clear(self) -> None: ...
