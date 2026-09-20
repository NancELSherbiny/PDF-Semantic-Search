"""VectorStore interface — the abstraction the app depends on."""

from __future__ import annotations

from abc import ABC, abstractmethod


class VectorStore(ABC):
    """A store of chunk embeddings that supports upsert and similarity search."""

    @abstractmethod
    def ensure_ready(self) -> None:
        """Create the underlying collection/index if it does not exist yet."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of stored chunks."""

    @abstractmethod
    def upsert(self, document: str, chunks: list[str], vectors: list[list[float]]) -> int:
        """Store each chunk with its vector and source document. Returns the count."""

    @abstractmethod
    def search(
        self, vector: list[float], top_k: int, score_threshold: float | None = None
    ) -> list[dict]:
        """Return up to top_k nearest chunks (score >= score_threshold) as dicts."""
