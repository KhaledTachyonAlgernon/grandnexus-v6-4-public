"""Bridge from metacognitive observations to explicit learning proposals."""
from __future__ import annotations

from typing import Any

from .learning_experiment import LearningProposal, SlowLearningStore
from .metacognition_loop import MetacognitionLoop


class LearningController:
    def __init__(self, meta: MetacognitionLoop, store: SlowLearningStore, min_observations: int = 3):
        if min_observations < 1:
            raise ValueError('min_observations must be positive')
        self.meta = meta
        self.store = store
        self.min_observations = min_observations

    def propose_if_ready(self, change: dict[str, Any], hypothesis: str) -> LearningProposal | None:
        review = self.meta.review()
        if review.count < self.min_observations:
            return None
        if review.recommendation == 'reduce_confidence_or_request_verification':
            return None
        return self.store.propose(change, hypothesis)
