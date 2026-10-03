"""Small persistent semantic graph preserving epistemic status and provenance."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import sqlite3
from pathlib import Path
import uuid


class GraphStatus(str, Enum):
    OBSERVATION = 'observation'
    HYPOTHESIS = 'hypothesis'
    VALIDATED = 'validated'
    REJECTED = 'rejected'


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    label: str
    kind: str = 'concept'
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GraphRelation:
    relation_id: str
    source_id: str
    predicate: str
    target_id: str
    status: GraphStatus
    confidence: float
    provenance: tuple[str, ...] = ()
    version: str | None = None


class SemanticGraph:
    def __init__(self, db_file: str | Path):
        self.db_file = str(db_file)
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS graph_nodes (node_id TEXT PRIMARY KEY, label TEXT NOT NULL, kind TEXT NOT NULL, metadata TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS graph_relations (relation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, predicate TEXT NOT NULL, target_id TEXT NOT NULL, status TEXT NOT NULL, confidence REAL NOT NULL, provenance TEXT NOT NULL, version TEXT)')

    def add_node(self, label: str, kind: str = 'concept', metadata: dict | None = None, node_id: str | None = None) -> GraphNode:
        if not label.strip():
            raise ValueError('label must be non-empty')
        node = GraphNode(node_id or str(uuid.uuid4()), label.strip(), kind, metadata or {})
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT OR REPLACE INTO graph_nodes VALUES (?, ?, ?, ?)', (node.node_id, node.label, node.kind, json.dumps(node.metadata, ensure_ascii=False)))
        return node

    def relate(self, source: GraphNode | str, predicate: str, target: GraphNode | str, status: GraphStatus = GraphStatus.OBSERVATION, confidence: float = 0.5, provenance: tuple[str, ...] = (), version: str | None = None) -> GraphRelation:
        if not predicate.strip() or not 0.0 <= confidence <= 1.0:
            raise ValueError('predicate must be non-empty and confidence must be between 0 and 1')
        source_id = source.node_id if isinstance(source, GraphNode) else source
        target_id = target.node_id if isinstance(target, GraphNode) else target
        relation = GraphRelation(str(uuid.uuid4()), source_id, predicate.strip(), target_id, status, confidence, provenance, version)
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT INTO graph_relations VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (relation.relation_id, relation.source_id, relation.predicate, relation.target_id, relation.status.value, relation.confidence, json.dumps(relation.provenance), relation.version))
        return relation

    def neighbors(self, node: GraphNode | str, validated_only: bool = False) -> list[GraphRelation]:
        node_id = node.node_id if isinstance(node, GraphNode) else node
        query = 'SELECT * FROM graph_relations WHERE (source_id = ? OR target_id = ?)'
        params = [node_id, node_id]
        if validated_only:
            query += " AND status = 'validated'"
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute(query, params).fetchall()
        return [GraphRelation(row[0], row[1], row[2], row[3], GraphStatus(row[4]), row[5], tuple(json.loads(row[6])), row[7]) for row in rows]

    def validated_relations(self) -> list[GraphRelation]:
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute("SELECT * FROM graph_relations WHERE status = 'validated'").fetchall()
        return [GraphRelation(row[0], row[1], row[2], row[3], GraphStatus(row[4]), row[5], tuple(json.loads(row[6])), row[7]) for row in rows]
