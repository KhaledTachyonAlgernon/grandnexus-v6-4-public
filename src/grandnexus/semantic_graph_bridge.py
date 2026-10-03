"""Project epistemic semantic statements into the local graph."""
from __future__ import annotations

from .semantic_graph import GraphNode, GraphStatus, SemanticGraph
from .semantic_knowledge import EpistemicStatus, SemanticStatement


class SemanticGraphBridge:
    def __init__(self, graph: SemanticGraph):
        self.graph = graph

    @staticmethod
    def _status(status: EpistemicStatus) -> GraphStatus:
        return GraphStatus(status.value)

    def project(self, statement: SemanticStatement) -> tuple[GraphNode, GraphNode, object]:
        source = self.graph.add_node(statement.subject, kind='entity', node_id=f'entity:{statement.subject.lower()}')
        target = self.graph.add_node(statement.object, kind='concept', node_id=f'concept:{statement.object.lower()}')
        relation = self.graph.relate(source, statement.predicate, target, self._status(statement.status), statement.confidence, statement.provenance, statement.metadata.get('version'))
        return source, target, relation
