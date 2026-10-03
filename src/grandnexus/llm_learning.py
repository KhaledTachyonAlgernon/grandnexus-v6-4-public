"""Controlled ingestion of LLM proposals into epistemic memory."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .llm_bridge import ExtractionCandidate
from .llm_verifier import VerificationResult
from .semantic_knowledge import SemanticKnowledgeBase


@dataclass(frozen=True)
class IngestionResult:
    candidate: ExtractionCandidate
    status: str
    statement_id: str | None
    reason: str


class LLMLearningGate:
    def __init__(self, knowledge: SemanticKnowledgeBase, source_prefix: str = 'llm'):
        self.knowledge = knowledge
        self.source_prefix = source_prefix

    def ingest(self, candidates: Iterable[ExtractionCandidate], verified: Iterable[VerificationResult] = ()) -> list[IngestionResult]:
        verified_by_key = {(item.candidate.subject.lower(), item.candidate.predicate.lower(), item.candidate.object.lower()): item for item in verified}
        output = []
        for candidate in candidates:
            check = verified_by_key.get((candidate.subject.lower(), candidate.predicate.lower(), candidate.object.lower()))
            if check is not None and check.status == 'contradicted':
                output.append(IngestionResult(candidate, 'rejected', None, 'candidate contradicts known statement'))
                continue
            statement = self.knowledge.observe(candidate.subject, candidate.predicate, candidate.object, f'{self.source_prefix}:{candidate.source}', candidate.confidence, {'origin': 'llm', 'status': 'hypothesis'})
            output.append(IngestionResult(candidate, 'hypothesis', statement.statement_id, 'stored pending independent validation'))
        return output
