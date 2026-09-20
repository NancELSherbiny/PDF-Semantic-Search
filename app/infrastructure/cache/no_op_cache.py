"""No-op cache: the default when caching is disabled.

Lets SearchService depend on the Cache interface unconditionally — no branching
on "is caching enabled?" in business logic.
"""

from __future__ import annotations

from typing import Any

from app.infrastructure.cache.cache import Cache


class NoOpCache(Cache):
    async def get(self, key: str) -> Any | None:
        return None

    async def set(self, key: str, value: Any) -> None:
        return None

    async def delete(self, key: str) -> None:
        return None

    async def clear(self) -> None:
        return None
