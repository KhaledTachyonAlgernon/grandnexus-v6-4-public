"""Hardware-independent contracts for perception and action MVPs."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
import uuid


@dataclass(frozen=True)
class PerceptionEvent:
    modality: Literal['vision', 'audio']
    payload: Any
    confidence: float
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if self.modality not in ('vision', 'audio'):
            raise ValueError('unsupported modality')
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError('confidence must be between 0 and 1')
        if not self.source:
            raise ValueError('source must be non-empty')


@dataclass(frozen=True)
class ActionRequest:
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    simulation: bool = True
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if not self.action.strip():
            raise ValueError('action must be non-empty')


@dataclass(frozen=True)
class ActionResult:
    request_id: str
    accepted: bool
    executed: bool
    simulation: bool
    message: str
    state: dict[str, Any] = field(default_factory=dict)
