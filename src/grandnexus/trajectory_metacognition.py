"""Consultative trajectory-level metacognition for simulated autonomy."""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import Iterable


@dataclass(frozen=True)
class TrajectoryAssessment:
    status: str
    novelty: float
    repeated_pattern: tuple[str, ...]
    pattern_repetitions: int
    window_size: int
    reason: str


class TrajectoryMetacognition:
    """Observes behavioural trajectories without deciding truth or action.

    A reflective pause is a soft intervention: it records a pending review and
    temporarily lets normal drive selection resume. It does not ban a repeated
    action, alter stored facts or create synthetic goals.
    """

    def __init__(self, window: int = 12, min_pattern_repetitions: int = 3, cooldown_cycles: int = 4):
        if window < 4:
            raise ValueError('window must be at least 4')
        if min_pattern_repetitions < 2:
            raise ValueError('min_pattern_repetitions must be at least 2')
        self.window = window
        self.min_pattern_repetitions = min_pattern_repetitions
        self.cooldown_cycles = cooldown_cycles
        self.objectives: list[str] = []
        self.seen_facts: set[str] = set()
        self._cooldown = 0

    def observe(self, objective: str | None, facts_before: Iterable[str], facts_after: Iterable[str]) -> None:
        if objective:
            self.objectives.append(objective)
            # A successful simulated objective denotes an effect already visited,
            # even if the caller records only a compact state snapshot.
            self.seen_facts.add(objective)
        self.seen_facts.update(facts_before)
        self.seen_facts.update(facts_after)
        if self._cooldown:
            self._cooldown -= 1

    def _pattern(self) -> tuple[tuple[str, ...], int]:
        recent = self.objectives[-self.window:]
        if len(recent) < 4:
            return (), 0
        for length in range(2, min(4, len(recent) // self.min_pattern_repetitions) + 1):
            pattern = tuple(recent[-length:])
            repetitions = 0
            cursor = len(recent)
            while cursor >= length and tuple(recent[cursor - length:cursor]) == pattern:
                repetitions += 1
                cursor -= length
            if repetitions >= self.min_pattern_repetitions:
                return pattern, repetitions
        return (), 0

    def assess(self, candidate_objectives: Iterable[str], state: Iterable[str]) -> TrajectoryAssessment:
        candidates = list(candidate_objectives)
        state_set = set(state)
        novel_candidates = [objective for objective in candidates if objective not in self.seen_facts and objective not in state_set]
        novelty = round(len(novel_candidates) / len(candidates), 4) if candidates else 0.0
        pattern, repetitions = self._pattern()
        if self._cooldown:
            return TrajectoryAssessment('cooldown', novelty, pattern, repetitions, min(len(self.objectives), self.window), 'recent reflective pause; ordinary drive selection remains available')
        if pattern and novelty == 0.0:
            return TrajectoryAssessment('stagnating', novelty, pattern, repetitions, min(len(self.objectives), self.window), 'repeated objective pattern with no unobserved achievable effect')
        return TrajectoryAssessment('normal', novelty, pattern, repetitions, min(len(self.objectives), self.window), 'trajectory retains novelty or lacks stable repetition')

    def mark_reflective_pause(self) -> None:
        self._cooldown = self.cooldown_cycles

    def counts(self) -> Counter[str]:
        return Counter(self.objectives)
