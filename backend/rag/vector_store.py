from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np

from rag.chunking import TextChunk
from rag.embeddings import get_embedding_backend


@dataclass
class RetrievedChunk:
    chunk: TextChunk
    score: float


class LocalVectorStore:
    def __init__(self, chunks: list[TextChunk]) -> None:
        self.chunks = chunks
        self._embedding_backend = get_embedding_backend()
        self._index = self._build_index(chunks)

    def _build_index(self, chunks: list[TextChunk]) -> faiss.Index:
        texts = [chunk.text for chunk in chunks]
        embeddings = self._embedding_backend.embed(texts)

        if embeddings.size == 0:
            raise ValueError("Cannot build a vector index without chunks.")

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        self._embeddings = embeddings
        return index

    def search(self, query: str, top_k: int = 5, *, source: str | None = None) -> list[RetrievedChunk]:
        if not self.chunks:
            return []

        query_embedding = self._embedding_backend.embed([query])
        scores, indices = self._index.search(query_embedding, min(top_k, len(self.chunks)))

        results: list[RetrievedChunk] = []
        for score, chunk_index in zip(scores[0], indices[0], strict=False):
            if chunk_index < 0:
                continue

            chunk = self.chunks[int(chunk_index)]
            if source is not None and chunk.source != source:
                continue

            results.append(RetrievedChunk(chunk=chunk, score=float(score)))

        return results[:top_k]
