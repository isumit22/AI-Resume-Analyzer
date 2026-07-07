from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    source: str
    index: int
    text: str


def split_text_into_chunks(text: str, *, source: str, chunk_size: int = 900, overlap: int = 150) -> list[TextChunk]:
    normalized_text = " ".join(text.split())
    if not normalized_text:
        return []

    chunks: list[TextChunk] = []
    start = 0
    index = 1

    while start < len(normalized_text):
        end = min(len(normalized_text), start + chunk_size)
        chunk_text = normalized_text[start:end].strip()
        if chunk_text:
            chunks.append(TextChunk(source=source, index=index, text=chunk_text))
            index += 1

        if end >= len(normalized_text):
            break

        start = max(0, end - overlap)

    return chunks
