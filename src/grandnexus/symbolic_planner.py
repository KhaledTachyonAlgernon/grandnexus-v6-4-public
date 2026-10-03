"""Bounded symbolic planning and simulation for GrandNexus."""
from __future__ import annotations

from dataclasses import dataclass

from .branch_contracts import CognitivePlan, PlanStep


@dataclass(frozen=True)
class SimAction:
    name: str
    preconditions: frozenset[str]
    effects: frozenset[str]
    deletes: frozenset[str] = frozenset()
    risk: str = 'low'


@dataclass(frozen=True)
class SimulationResult:
    success: bool
    final_state: frozenset[str]
    executed: tuple[str, ...]
    failed_step: str | None = None
    message: str = ''


class SymbolicPlanner:
    def __init__(self, actions: list[SimAction]):
        self.actions = tuple(actions)

    def plan(self, objective: str, state: set[str], request_id: str = 'simulation') -> CognitivePlan:
        if not objective.strip():
            raise ValueError('objective must be non-empty')
        target = objective.strip()
        current = set(state)
        steps: list[PlanStep] = []
        visiting: set[str] = set()

        def build(goal: str) -> bool:
            if goal in current:
                return True
            if goal in visiting:
                return False
            visiting.add(goal)
            action = next((candidate for candidate in self.actions if goal in candidate.effects), None)
            if action is None:
                visiting.remove(goal)
                return False
            for precondition in action.preconditions:
                if not build(precondition):
                    visiting.remove(goal)
                    return False
            steps.append(PlanStep(action.name, action.name, tuple(sorted(action.preconditions)), action.risk))
            current.difference_update(action.deletes)
            current.update(action.effects)
            visiting.remove(goal)
            return True

        success = build(target)
        return CognitivePlan(request_id, tuple(steps) if success else (), 1.0 if success else 0.0, simulation_only=True)

    def simulate(self, plan: CognitivePlan, state: set[str]) -> SimulationResult:
        current = set(state)
        executed: list[str] = []
        by_name = {action.name: action for action in self.actions}
        for step in plan.steps:
            action = by_name.get(step.step_id)
            if action is None:
                return SimulationResult(False, frozenset(current), tuple(executed), step.step_id, 'unknown action')
            if not action.preconditions <= current:
                return SimulationResult(False, frozenset(current), tuple(executed), step.step_id, 'preconditions not satisfied')
            current -= set(action.deletes)
            current |= set(action.effects)
            executed.append(action.name)
        return SimulationResult(True, frozenset(current), tuple(executed), message='simulation completed')
