"""Guarded extension around the legacy symbolic planner."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .branch_contracts import CognitivePlan
from .symbolic_planner import SimAction, SymbolicPlanner


@dataclass(frozen=True)
class PlanningDecision:
    accepted: bool
    plan: CognitivePlan | None
    reason: str
    risk: str = 'low'
    objectives: tuple[str, ...] = ()


class AdvancedPlanner:
    def __init__(self, actions: Iterable[SimAction], max_risk: str = 'medium'):
        self.planner = SymbolicPlanner(list(actions))
        self.max_risk = max_risk
        self._risk_order = {'low': 0, 'medium': 1, 'high': 2}

    def plan_compound(self, objectives: Iterable[str], state: set[str], request_id: str = 'compound', conflicts: Iterable[tuple[str, str]] = ()) -> PlanningDecision:
        goals = tuple(goal.strip() for goal in objectives if goal and goal.strip())
        unresolved = tuple(conflicts)
        if unresolved:
            return PlanningDecision(False, None, f'episodic state conflict: {unresolved}', 'low', goals)
        if not goals:
            return PlanningDecision(False, None, 'no objectives')
        combined_steps = []
        current = set(state)
        max_risk = 'low'
        for goal in goals:
            if goal in current:
                continue
            plan = self.planner.plan(goal, current, request_id)
            if not plan.steps:
                return PlanningDecision(False, None, f'objective not reachable: {goal}', max_risk, goals)
            combined_steps.extend(plan.steps)
            for action in self.planner.actions:
                if action.name in {step.step_id for step in plan.steps}:
                    current -= set(action.deletes)
                    current |= set(action.effects)
                    if self._risk_order.get(action.risk, 2) > self._risk_order.get(max_risk, 0):
                        max_risk = action.risk
        if self._risk_order.get(max_risk, 2) > self._risk_order.get(self.max_risk, 1):
            return PlanningDecision(False, None, f'risk exceeds policy: {max_risk}', max_risk, goals)
        compound = CognitivePlan(request_id, tuple(combined_steps), 1.0, simulation_only=True)
        return PlanningDecision(True, compound, 'plan accepted for simulation', max_risk, goals)
