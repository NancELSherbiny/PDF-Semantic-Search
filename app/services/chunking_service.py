"""Split extracted text into overlapping word-chunks for embedding."""

from __future__ import annotations

from app.core.config import Settings


class ChunkingService:
    def __init__(self, settings: Settings) -> None:
        self._chunk_size = settings.chunk_size
        self._overlap = settings.chunk_overlap
        if self._overlap >= self._chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

    def chunk(self, text: str) -> list[str]:
        """chunk_size stays under the model's token limit; overlap keeps ideas
        whole across boundaries. Empty/whitespace-only text returns []."""
        words = text.split()
        if not words:
            return []
        step = self._chunk_size - self._overlap
        chunks: list[str] = []
        for start in range(0, len(words), step):
            chunks.append(" ".join(words[start:start + self._chunk_size]))
            if start + self._chunk_size >= len(words):  # reached the end
                break
        return chunks
