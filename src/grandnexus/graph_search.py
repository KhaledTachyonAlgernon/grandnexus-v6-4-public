"""Explainable search over the local semantic graph."""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from pathlib import Path
import re

from .semantic_graph import GraphStatus, SemanticGraph


@dataclass(frozen=True)
class GraphSearchHit:
    node_id: str
    label: str
    relation_id: str | None
    predicate: str | None
    related_node_id: str | None
    status: GraphStatus | None
    score: float
    provenance: tuple[str, ...] = ()


class GraphSemanticSearch:
    def __init__(self, graph: SemanticGraph):
        self.graph = graph

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {token.lower() for token in re.findall(r"[\wÀ-ÿ]+", value) if len(token) > 2}

    def search(self, query: str, validated_only: bool = False, limit: int = 10) -> list[GraphSearchHit]:
        terms = self._terms(query)
        if not terms:
            return []
        status_filter = " AND r.status = 'validated'" if validated_only else ''
        with sqlite3.connect(self.graph.db_file) as conn:
            rows = conn.execute(f"""SELECT n.node_id, n.label, r.relation_id, r.predicate,
                r.target_id, r.status, r.confidence, r.provenance
                FROM graph_nodes n LEFT JOIN graph_relations r ON r.source_id = n.node_id
                WHERE n.label LIKE ? OR r.predicate LIKE ? OR r.target_id LIKE ? {status_filter}""", tuple(f'%{query}%' for _ in range(3))).fetchall()
            target_rows = conn.execute(f"""SELECT n.node_id, n.label, r.relation_id, r.predicate,
                r.source_id, r.status, r.confidence, r.provenance
                FROM graph_nodes n LEFT JOIN graph_relations r ON r.target_id = n.node_id
                WHERE n.label LIKE ? OR r.predicate LIKE ? OR r.source_id LIKE ? {status_filter}""", tuple(f'%{query}%' for _ in range(3))).fetchall()
        hits = []
        for node_id, label, relation_id, predicate, related_id, status, confidence, provenance in rows + target_rows:
            if relation_id is None or confidence is None:
                continue
            label_terms = self._terms(label or '')
            predicate_terms = self._terms(predicate or '')
            score = confidence * (len(terms & (label_terms | predicate_terms)) / len(terms)) if (label_terms | predicate_terms) else 0.0
            if score > 0:
                hits.append(GraphSearchHit(node_id, label, relation_id, predicate, related_id, GraphStatus(status) if status else None, score, tuple(__import__('json').loads(provenance)) if provenance else ()))
        return sorted(hits, key=lambda hit: (-hit.score, hit.node_id, hit.relation_id or ''))[:limit]
