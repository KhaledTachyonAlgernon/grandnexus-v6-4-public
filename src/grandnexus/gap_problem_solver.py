"""Symbolic, non-intrusive diagnosis of unmet cognitive gaps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .symbolic_planner import SimAction


@dataclass(frozen=True)
class GapHypothesis:
    gap_id: str
    category: str
    target_effect: str | None
    missing_facts: tuple[str, ...]
    blocked_actions: tuple[str, ...]
    verification_question: str
    provenance: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class GapAnalysis:
    status: str
    hypotheses: tuple[GapHypothesis, ...]
    reason: str


class GapProblemSolver:
    """Finds missing symbolic conditions without treating them as facts.

    The solver has no access to `WorldStateLedger.apply_transition`, semantic
    promotion or action execution. Its output is a shadow-only explanation and
    a verification question that another subsystem may later evaluate.
    """

    def __init__(self, actions: Iterable[SimAction], max_hypotheses: int = 3):
        self.actions = tuple(actions)
        self.max_hypotheses = max_hypotheses

    @staticmethod
    def _unobserved(effect: str, seen_effects: set[str], state: set[str]) -> bool:
        return effect not in seen_effects and effect not in state

    def analyze(
        self,
        state: Iterable[str],
        seen_effects: Iterable[str],
        conflicts: Iterable[tuple[str, str]] = (),
        trajectory_pattern: Iterable[str] = (),
    ) -> GapAnalysis:
        current = set(state)
        seen = set(seen_effects)
        unresolved = tuple(sorted(tuple(pair) for pair in conflicts))
        if unresolved:
            return GapAnalysis(
                'blocked_by_conflict',
                (),
                f'current-state conflict prevents gap diagnosis: {unresolved}',
            )

        candidates: list[GapHypothesis] = []
        for action in self.actions:
            novel_effects = sorted(effect for effect in action.effects if self._unobserved(effect, seen, current))
            missing = tuple(sorted(set(action.preconditions) - current))
            if not novel_effects or not missing:
                continue
            for effect in novel_effects:
                gap_id = f'{action.name}:{effect}:{"|".join(missing)}'
                question = f'verify whether {", ".join(missing)} is available before attempting {action.name} for {effect}'
                candidates.append(GapHypothesis(
                    gap_id=gap_id,
                    category='missing_precondition',
                    target_effect=effect,
                    missing_facts=missing,
                    blocked_actions=(action.name,),
                    verification_question=question,
                    provenance=('symbolic-action-preconditions', 'trajectory-metacognition'),
                    confidence=0.55,
                ))

        # Merge duplicate missing sets, retaining the effects/actions that make
        # the same verification question useful across several pathways.
        grouped: dict[tuple[str, ...], list[GapHypothesis]] = {}
        for item in candidates:
            grouped.setdefault(item.missing_facts, []).append(item)
        merged: list[GapHypothesis] = []
        for missing, items in grouped.items():
            effects = tuple(sorted({item.target_effect for item in items if item.target_effect}))
            actions = tuple(sorted({action for item in items for action in item.blocked_actions}))
            target = effects[0] if len(effects) == 1 else None
            merged.append(GapHypothesis(
                gap_id=f'gap:{"|".join(missing)}',
                category='missing_precondition',
                target_effect=target,
                missing_facts=missing,
                blocked_actions=actions,
                verification_question=f'verify whether {", ".join(missing)} is available; it blocks {", ".join(actions)}',
                provenance=('symbolic-action-preconditions', 'trajectory-metacognition'),
                confidence=min(0.75, 0.45 + 0.05 * len(items)),
            ))
        merged.sort(key=lambda item: (-item.confidence, item.missing_facts, item.blocked_actions))

        if merged:
            return GapAnalysis(
                'hypotheses_available',
                tuple(merged[:self.max_hypotheses]),
                f'{len(merged)} symbolic verification gap(s) derived from currently blocked novel effects',
            )
        if tuple(trajectory_pattern):
            return GapAnalysis(
                'no_symbolic_gap',
                (),
                'repetition is visible but the current action model exposes no unobserved blocked effect',
            )
        return GapAnalysis('not_applicable', (), 'no trajectory stagnation or symbolic gap to analyse')
