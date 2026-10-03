"""Cautious metacognition loop for confidence and error observation."""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any
import uuid


@dataclass(frozen=True)
class PredictionRecord:
    prediction_id: str
    confidence: float
    correct: bool | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MetacognitiveReview:
    count: int
    accuracy: float
    mean_confidence: float
    calibration_gap: float
    recommendation: str


class MetacognitionLoop:
    """Observe confidence versus outcomes; never silently rewrite knowledge."""

    def __init__(self):
        self.records: list[PredictionRecord] = []

    def register(self, confidence: float, context: dict[str, Any] | None = None) -> str:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError('confidence must be between 0 and 1')
        prediction_id = str(uuid.uuid4())
        self.records.append(PredictionRecord(prediction_id, confidence, None, context or {}))
        return prediction_id

    def observe(self, prediction_id: str, correct: bool) -> None:
        for index, record in enumerate(self.records):
            if record.prediction_id == prediction_id:
                self.records[index] = PredictionRecord(record.prediction_id, record.confidence, bool(correct), record.context)
                return
        raise KeyError(prediction_id)

    def review(self) -> MetacognitiveReview:
        completed = [record for record in self.records if record.correct is not None]
        if not completed:
            return MetacognitiveReview(0, 0.0, 0.0, 0.0, 'collect_more_outcomes')
        accuracy = mean(float(record.correct) for record in completed)
        confidence = mean(record.confidence for record in completed)
        gap = confidence - accuracy
        if gap > 0.15:
            recommendation = 'reduce_confidence_or_request_verification'
        elif gap < -0.15:
            recommendation = 'investigate_underconfidence'
        else:
            recommendation = 'calibration_within_tolerance'
        return MetacognitiveReview(len(completed), accuracy, confidence, gap, recommendation)
