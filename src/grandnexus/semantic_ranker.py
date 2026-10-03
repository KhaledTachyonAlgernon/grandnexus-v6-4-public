"""Optional semantic ranking adapter for the memory layer."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import math
import re
from typing import Protocol


@dataclass(frozen=True)
class RankedMemory:
    memory_id: str
    content: str
    score: float
    backend: str


class SemanticBackend(Protocol):
    name: str

    def rank(self, query: str, candidates: list[tuple[str, str]], limit: int) -> list[RankedMemory]:
        ...


class LexicalSemanticBackend:
    name = "lexical-fallback"

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {word.lower() for word in re.findall(r"[\wÀ-ÿ]+", value) if len(word) > 2}

    def rank(self, query: str, candidates: list[tuple[str, str]], limit: int) -> list[RankedMemory]:
        query_terms = self._terms(query)
        if not query_terms:
            return []
        ranked = []
        for memory_id, content in candidates:
            terms = self._terms(content)
            overlap = query_terms & terms
            if overlap:
                ranked.append(RankedMemory(memory_id, content, len(overlap) / math.sqrt(len(query_terms) * max(len(terms), 1)), self.name))
        return sorted(ranked, key=lambda item: (-item.score, item.memory_id))[:limit]


class SentenceTransformerBackend:
    name = "sentence-transformers"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if importlib.util.find_spec("sentence_transformers") is None:
            raise RuntimeError("sentence_transformers is not installed")
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def rank(self, query: str, candidates: list[tuple[str, str]], limit: int) -> list[RankedMemory]:
        import numpy as np
        query_vector = self.model.encode([query], normalize_embeddings=True)[0]
        texts = [content for _, content in candidates]
        vectors = self.model.encode(texts, normalize_embeddings=True)
        scores = np.dot(vectors, query_vector)
        ranked = [RankedMemory(memory_id, content, float(score), self.name) for (memory_id, content), score in zip(candidates, scores)]
        return sorted(ranked, key=lambda item: (-item.score, item.memory_id))[:limit]


class SemanticRanker:
    def __init__(self, backend: SemanticBackend | None = None, prefer_ml: bool = False):
        if backend is not None:
            self.backend = backend
        elif prefer_ml and importlib.util.find_spec("sentence_transformers") is not None:
            self.backend = SentenceTransformerBackend()
        else:
            self.backend = LexicalSemanticBackend()

    @property
    def backend_name(self) -> str:
        return self.backend.name

    def rank(self, query: str, candidates: list[tuple[str, str]], limit: int = 10) -> list[RankedMemory]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be non-empty")
        return self.backend.rank(query, candidates, limit)
