"""Shared contracts for future GrandNexus branches."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
import uuid


@dataclass(frozen=True)
class KnowledgeEnvelope:
    subject: str
    predicate: str
    object: str
    status: Literal['observation', 'hypothesis', 'validated', 'rejected']
    confidence: float
    provenance: tuple[str, ...] = ()
    version: str | None = None


@dataclass(frozen=True)
class CognitiveRequest:
    objective: str
    context: dict[str, Any] = field(default_factory=dict)
    constraints: tuple[str, ...] = ()
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    description: str
    preconditions: tuple[str, ...] = ()
    risk: Literal['low', 'medium', 'high'] = 'low'


@dataclass(frozen=True)
class CognitivePlan:
    request_id: str
    steps: tuple[PlanStep, ...]
    confidence: float
    simulation_only: bool = True


@dataclass(frozen=True)
class AgentMessage:
    sender: str
    recipient: str
    message_type: Literal['proposal', 'evidence', 'critique', 'decision']
    payload: dict[str, Any]
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
