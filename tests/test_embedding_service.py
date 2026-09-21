import numpy as np
import pytest

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService


class FakeModel:
    # Mirrors fastembed's TextEmbedding.embed: yields one np.ndarray per text.
    def embed(self, texts):
        return [np.array([0.1, 0.2, 0.3]) for _ in texts]


def test_embed_returns_one_vector_per_text():
    svc = EmbeddingService(Settings(), model=FakeModel())
    out = svc.embed(["a", "b"])
    assert len(out) == 2
    assert out[0] == pytest.approx([0.1, 0.2, 0.3])
    assert isinstance(out, list) and isinstance(out[0], list)


def test_dimension_is_derived_from_model():
    svc = EmbeddingService(Settings(), model=FakeModel())
    assert svc.dimension == 3
