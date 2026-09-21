"""
Convert text into vectors with an embedding model.

Uses fastembed (ONNX runtime) rather than torch: same model
(all-MiniLM-L6-v2, 384-dim) but a much smaller, faster-starting dependency.
The model is loaded once (in __init__) and reused; the model name comes from
settings, so the rest of the app is not coupled to a specific model.
"""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings, model: Any | None = None) -> None:
        if model is None:
            # Imported lazily and injectable so tests need no model download.
            from fastembed import TextEmbedding

            logger.info("Loading embedding model: %s", settings.embedding_model)
            model = TextEmbedding(model_name=settings.embedding_model)
        self._model = model
        # Derive the true dimension from the model so it can't silently disagree
        # with a separately-configured value.
        self.dimension = len(self.embed(["dimension probe"])[0])

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts; returns one vector per input.

        Qdrant's cosine distance normalises internally, so we store the model's
        raw vectors as-is.
        """
        return [vector.tolist() for vector in self._model.embed(texts)]
