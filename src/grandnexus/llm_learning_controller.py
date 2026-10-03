"""Coordinates LLM hypotheses with the existing slow-learning policy."""
from __future__ import annotations

from typing import Any

from .learning_controller import LearningController
from .llm_learning import IngestionResult


class LLMProposalCoordinator:
    def __init__(self, controller: LearningController):
        self.controller = controller

    def propose(self, ingestion: IngestionResult, hypothesis: str, change: dict[str, Any]):
        if ingestion.status != 'hypothesis' or ingestion.statement_id is None:
            return None
        change = dict(change)
        change['statement_id'] = ingestion.statement_id
        change['source'] = ingestion.candidate.source
        change['confidence'] = ingestion.candidate.confidence
        return self.controller.propose_if_ready(change, hypothesis)
