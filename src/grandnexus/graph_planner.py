"""Translate validated graph relations into bounded simulation planning inputs."""
from __future__ import annotations

from dataclasses import dataclass

from .semantic_graph import GraphStatus, SemanticGraph
from .symbolic_planner import SimAction, SymbolicPlanner


@dataclass(frozen=True)
class GraphPlanningContext:
    state: frozenset[str]
    validated_relation_ids: tuple[str, ...]
    contradiction_relation_ids: tuple[str, ...] = ()


class GraphPlanner:
    def __init__(self, graph: SemanticGraph, actions: list[SimAction]):
        self.graph = graph
        self.planner = SymbolicPlanner(actions)

    def context_for(self, node_id: str) -> GraphPlanningContext:
        relations = self.graph.neighbors(node_id, validated_only=True)
        state = {f'{relation.predicate}:{relation.target_id}' for relation in relations if relation.status == GraphStatus.VALIDATED}
        by_predicate = {}
        for relation in relations:
            by_predicate.setdefault((relation.source_id, relation.predicate), set()).add(relation.target_id)
        contradictory = {relation.relation_id for relation in relations if len(by_predicate[(relation.source_id, relation.predicate)]) > 1}
        return GraphPlanningContext(frozenset(state), tuple(relation.relation_id for relation in relations), tuple(sorted(contradictory)))

    def plan_from_context(self, objective: str, context: GraphPlanningContext, request_id: str = 'graph-plan'):
        if context.contradiction_relation_ids:
            raise ValueError('contradictory validated relations block planning')
        return self.planner.plan(objective, set(context.state), request_id)

    def simulate(self, plan, context: GraphPlanningContext):
        return self.planner.simulate(plan, set(context.state))
