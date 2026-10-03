"""Guarded hybrid retrieval: lexical anchors remain part of the decision."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .semantic_ranker import SemanticRanker, RankedMemory


@dataclass(frozen=True)
class HybridHit:
    memory_id: str
    content: str
    lexical_score: float
    semantic_score: float
    combined_score: float
    accepted: bool
    reason: str


class HybridSemanticSearch:
    def __init__(self, ranker: SemanticRanker | None = None, semantic_threshold: float = 0.45):
        self.ranker = ranker or SemanticRanker()
        self.semantic_threshold = semantic_threshold

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {token.lower() for token in re.findall(r"[\wÀ-ÿ]+", value) if len(token) > 2}

    def search(self, query: str, candidates: list[tuple[str, str]], limit: int = 10) -> list[HybridHit]:
        query_terms = self._terms(query)
        if not query_terms:
            raise ValueError('query must be non-empty')
        semantic = self.ranker.rank(query, candidates, len(candidates))
        by_id = {item.memory_id: item for item in semantic}
        hits = []
        for memory_id, content in candidates:
            semantic_item: RankedMemory | None = by_id.get(memory_id)
            semantic_score = semantic_item.score if semantic_item else 0.0
            lexical_terms = self._terms(content)
            lexical_score = len(query_terms & lexical_terms) / len(query_terms)
            combined = 0.35 * lexical_score + 0.65 * semantic_score
            accepted = bool(lexical_score > 0 or semantic_score >= self.semantic_threshold)
            reason = 'lexical-anchor' if lexical_score > 0 else ('semantic-threshold' if accepted else 'rejected-no-anchor')
            if accepted:
                hits.append(HybridHit(memory_id, content, lexical_score, semantic_score, combined, True, reason))
        return sorted(hits, key=lambda hit: (-hit.combined_score, hit.memory_id))[:limit]
