"""Verification gate between probabilistic LLM proposals and epistemic memory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .llm_bridge import ExtractionCandidate
from .semantic_knowledge import EpistemicStatus, SemanticKnowledgeBase


@dataclass(frozen=True)
class VerificationResult:
    candidate: ExtractionCandidate
    status: str
    supporting_statement_ids: tuple[str, ...] = ()
    contradiction_statement_ids: tuple[str, ...] = ()
    reason: str = ''

    @property
    def promotable(self) -> bool:
        return self.status == 'supported'


class LLMVerifier:
    def __init__(self, knowledge: SemanticKnowledgeBase):
        self.knowledge = knowledge

    def verify(self, candidates: Iterable[ExtractionCandidate]) -> list[VerificationResult]:
        results = []
        for candidate in candidates:
            matches = self.knowledge.search(candidate.subject, validated_only=False)
            exact = [item for item in matches if item.key() == (candidate.subject.lower(), candidate.predicate.lower(), candidate.object.lower())]
            supporting = tuple(item.statement_id for item in exact if item.status is EpistemicStatus.VALIDATED)
            contradictions = tuple(item.statement_id for item in exact if item.contradictions or item.status is EpistemicStatus.REJECTED)
            if supporting and not contradictions:
                status, reason = 'supported', 'exact validated statement exists'
            elif contradictions:
                status, reason = 'contradicted', 'matching statement has contradiction or rejection'
            else:
                status, reason = 'unverified', 'candidate has no exact validated support'
            results.append(VerificationResult(candidate, status, supporting, contradictions, reason))
        return results
