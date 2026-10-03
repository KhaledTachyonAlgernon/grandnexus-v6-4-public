"""Structured failure events for cautious observation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
import uuid

FailureCategory = Literal[
    'rejected_before_plan', 'unreachable_objective', 'precondition_failure',
    'simulation_failure', 'prediction_error', 'safety_stop'
]


@dataclass(frozen=True)
class FailureEvent:
    category: FailureCategory
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    counts_as_prediction_error: bool = False
    permits_learning_proposal: bool = False


class FailureRegistry:
    def __init__(self):
        self.events: list[FailureEvent] = []

    def record(self, category: FailureCategory, message: str, context: dict[str, Any] | None = None) -> FailureEvent:
        if not message.strip():
            raise ValueError('message must be non-empty')
        prediction_error = category == 'prediction_error'
        event = FailureEvent(category, message, context or {}, counts_as_prediction_error=prediction_error)
        self.events.append(event)
        return event

    def by_category(self, category: FailureCategory) -> list[FailureEvent]:
        return [event for event in self.events if event.category == category]
