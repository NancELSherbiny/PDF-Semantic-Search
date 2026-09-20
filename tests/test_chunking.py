import pytest

from app.core.config import Settings
from app.services.chunking_service import ChunkingService


def _service(chunk_size: int, overlap: int) -> ChunkingService:
    return ChunkingService(Settings(chunk_size=chunk_size, chunk_overlap=overlap))


def test_empty_text_returns_empty():
    assert _service(10, 2).chunk("   ") == []


def test_short_text_is_single_chunk():
    assert _service(10, 2).chunk("a b c") == ["a b c"]


def test_chunks_overlap():
    words = " ".join(str(i) for i in range(10))
    chunks = _service(4, 2).chunk(words)
    assert chunks[0] == "0 1 2 3"
    assert chunks[1] == "2 3 4 5"  # last 2 words repeat -> overlap
    assert chunks[-1].endswith("9")


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        _service(5, 5)
