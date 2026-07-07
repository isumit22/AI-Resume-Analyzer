from __future__ import annotations


def retrieve_relevant_chunks(query: str, chunks: list[str], limit: int = 3) -> list[str]:
    del query
    return chunks[:limit]
