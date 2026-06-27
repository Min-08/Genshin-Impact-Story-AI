from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


class VectorRetriever(Protocol):
    def search(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        """Return semantic search hits using the same hit shape as the main engine."""


@dataclass
class NullVectorRetriever:
    reason: str = "vector index is not configured"

    def search(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        return []


def open_vector_retriever(root: Path, backend: str = "none") -> VectorRetriever:
    if backend == "none":
        return NullVectorRetriever()
    raise NotImplementedError(
        f"Vector backend '{backend}' is not implemented yet. "
        "Add an embedding index under data/processed/vector before enabling it."
    )
