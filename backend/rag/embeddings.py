from __future__ import annotations

from functools import lru_cache

import numpy as np


class EmbeddingBackend:
    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


class SentenceTransformerBackend(EmbeddingBackend):
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed(self, texts: list[str]) -> np.ndarray:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(embeddings, dtype=np.float32)


class HashingFallbackBackend(EmbeddingBackend):
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimensions), dtype=np.float32)

        for row_index, text in enumerate(texts):
            for token in text.lower().split():
                bucket = hash(token) % self.dimensions
                vectors[row_index, bucket] += 1.0

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms


@lru_cache(maxsize=1)
def get_embedding_backend() -> EmbeddingBackend:
    try:
        return SentenceTransformerBackend()
    except Exception:
        return HashingFallbackBackend()
