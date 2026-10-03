"""Explainable comparison of already generated simulation plans."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .branch_contracts import CognitivePlan


@dataclass(frozen=True)
class PlanScore:
    plan: CognitivePlan
    cost: int
    risk: str
    risk_value: int
    score: tuple[float, int, int]


@dataclass(frozen=True)
class PlanSelection:
    status: str
    selected: CognitivePlan | None
    ranked: tuple[PlanScore, ...]
    reason: str


class PlanEvaluator:
    _risk_order = {'low': 0, 'medium': 1, 'high': 2}

    def score(self, plan: CognitivePlan) -> PlanScore:
        risks = [getattr(step, 'risk', 'low') for step in plan.steps]
        risk = max(risks, key=lambda value: self._risk_order.get(value, 2), default='low')
        risk_value = self._risk_order.get(risk, 2)
        cost = len(plan.steps)
        return PlanScore(plan, cost, risk, risk_value, (-plan.confidence, risk_value, cost))

    def select(self, plans: Iterable[CognitivePlan], max_risk: str = 'medium') -> PlanSelection:
        candidates = [self.score(plan) for plan in plans if plan.simulation_only and plan.steps]
        allowed = [item for item in candidates if item.risk_value <= self._risk_order.get(max_risk, 1)]
        ranked = tuple(sorted(allowed, key=lambda item: item.score))
        if not ranked:
            return PlanSelection('unresolved', None, tuple(sorted(candidates, key=lambda item: item.score)), 'no acceptable simulation plan')
        best = ranked[0]
        equivalent = [item for item in ranked if item.score == best.score]
        if len(equivalent) > 1:
            return PlanSelection('clarification_required', None, ranked, 'multiple equivalent plans remain')
        return PlanSelection('selected', best.plan, ranked, 'lowest risk and cost among acceptable plans')
