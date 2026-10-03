"""Small explainable ontology view over validated graph relations."""
from __future__ import annotations

from dataclasses import dataclass

from .semantic_graph import GraphStatus, SemanticGraph


@dataclass(frozen=True)
class OntologyView:
    node_id: str
    relation_ids: tuple[str, ...]
    predicates: tuple[str, ...]
    targets: tuple[str, ...]
    ambiguities: tuple[str, ...] = ()


class OntologyAnalyzer:
    def __init__(self, graph: SemanticGraph):
        self.graph = graph

    def view(self, node_id: str) -> OntologyView:
        relations = self.graph.neighbors(node_id, validated_only=True)
        predicates = sorted({relation.predicate for relation in relations})
        targets = sorted({relation.target_id for relation in relations})
        by_predicate: dict[str, set[str]] = {}
        for relation in relations:
            if relation.status is GraphStatus.VALIDATED:
                by_predicate.setdefault(relation.predicate, set()).add(relation.target_id)
        ambiguities = tuple(sorted(predicate for predicate, values in by_predicate.items() if len(values) > 1))
        return OntologyView(node_id, tuple(relation.relation_id for relation in relations), tuple(predicates), tuple(targets), ambiguities)
