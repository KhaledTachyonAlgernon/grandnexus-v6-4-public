"""Bridge that prevents raw perception from becoming validated knowledge."""
from __future__ import annotations

from .hardware_contracts import PerceptionEvent
from .semantic_knowledge import SemanticKnowledgeBase, SemanticStatement
from .symbolic_reasoner import Fact


class SemanticMemoryBridge:
    def __init__(self, knowledge_base: SemanticKnowledgeBase):
        self.knowledge_base = knowledge_base

    def record_perception(self, event: PerceptionEvent, subject: str, predicate: str, object: str) -> SemanticStatement:
        return self.knowledge_base.observe(subject, predicate, object, source=event.source, confidence=event.confidence, metadata={'event_id': event.event_id, 'modality': event.modality})

    def validated_facts(self, subject: str | None = None) -> list[Fact]:
        statements = self.knowledge_base.search('', validated_only=True) if subject is None else self.knowledge_base.search(subject, validated_only=True)
        return [Fact(statement.subject, f'{statement.predicate} {statement.object}') for statement in statements]
