"""Optional advanced reasoning interface with a deterministic local fallback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AdvancedReasoningOutput:
    statement: str
    confidence: float
    engine: str


class ReasoningBackend(Protocol):
    name: str

    def reason(self, text: str) -> AdvancedReasoningOutput:
        ...


class DeterministicAdvancedBackend:
    """Local backend used until a real ML backend is explicitly configured."""
    name = "heuristic-local"

    def reason(self, text: str) -> AdvancedReasoningOutput:
        normalized = text.strip()
        lower = normalized.lower()
        if any(token in lower for token in ("pourquoi", "cause", "raison")):
            statement = "The input requests causal analysis."
        elif any(token in lower for token in ("comment", "étape", "plan")):
            statement = "The input requests a procedural plan."
        elif normalized.endswith("?"):
            statement = "The input is an explicit question."
        else:
            statement = "The input is a declarative statement."
        return AdvancedReasoningOutput(statement=statement, confidence=0.75, engine=self.name)


class AdvancedReasoner:
    """Facade selecting an optional backend while guaranteeing a safe fallback."""

    def __init__(self, backend: ReasoningBackend | None = None):
        self.backend = backend or DeterministicAdvancedBackend()

    @property
    def engine_name(self) -> str:
        return getattr(self.backend, "name", type(self.backend).__name__)

    def reason(self, text: str) -> AdvancedReasoningOutput:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        try:
            output = self.backend.reason(text)
            if not isinstance(output, AdvancedReasoningOutput):
                raise TypeError("backend must return AdvancedReasoningOutput")
            return output
        except Exception:
            fallback = DeterministicAdvancedBackend()
            return fallback.reason(text)
