"""Bounded problem solving over validated knowledge and simulation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .graph_planner import GraphPlanner, GraphPlanningContext
from .ontology_analysis import OntologyAnalyzer, OntologyView
from .plan_evaluator import PlanEvaluator, PlanSelection
from .semantic_graph import SemanticGraph
from .symbolic_planner import SimulationResult


@dataclass(frozen=True)
class ProblemUnderstanding:
    objective: str
    known_state: tuple[str, ...]
    validated_relations: tuple[str, ...]
    unknowns: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    ontology: OntologyView | None = None


@dataclass(frozen=True)
class ProblemSolution:
    understanding: ProblemUnderstanding
    status: str
    plan: Any = None
    simulation: SimulationResult | None = None
    reason: str = ''
    trace: tuple[str, ...] = field(default_factory=tuple)


class ProblemSolver:
    def __init__(self, graph: SemanticGraph, actions):
        self.graph_planner = GraphPlanner(graph, list(actions))
        self.ontology = OntologyAnalyzer(graph)
        self.plan_evaluator = PlanEvaluator()

    def understand(self, node_id: str, objective: str) -> ProblemUnderstanding:
        if not objective.strip():
            raise ValueError('objective must be non-empty')
        context = self.graph_planner.context_for(node_id)
        ontology = self.ontology.view(node_id)
        unknowns = () if objective in context.state else (objective,)
        return ProblemUnderstanding(objective, tuple(sorted(context.state)), context.validated_relation_ids, unknowns, context.contradiction_relation_ids, (), ontology)

    def compare_plans(self, plans, max_risk: str = 'medium') -> PlanSelection:
        return self.plan_evaluator.select(plans, max_risk=max_risk)

    def solve(self, node_id: str, objective: str, request_id: str = 'problem-solver') -> ProblemSolution:
        understanding = self.understand(node_id, objective)
        trace = ['understanding_built']
        if understanding.contradictions:
            return ProblemSolution(understanding, 'blocked', reason='validated graph contradictions block solving', trace=tuple(trace + ['contradiction_detected']))
        try:
            context = self.graph_planner.context_for(node_id)
            plan = self.graph_planner.plan_from_context(objective, context, request_id)
        except ValueError as exc:
            return ProblemSolution(understanding, 'unresolved', reason=str(exc), trace=tuple(trace + ['planning_refused']))
        if not plan.steps and objective not in context.state:
            return ProblemSolution(understanding, 'unresolved', plan=plan, reason='objective is unreachable from validated state', trace=tuple(trace + ['planning_refused']))
        trace.append('plan_built')
        simulation = self.graph_planner.simulate(plan, context)
        trace.append('simulation_completed' if simulation.success else 'simulation_failed')
        return ProblemSolution(understanding, 'solved' if simulation.success else 'failed', plan, simulation, 'objective reached' if simulation.success else simulation.message, tuple(trace))
