"""Epistemic semantic memory: observations are not automatically knowledge."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

from .source_reputation import SourceProfile, assess_evidence


class EpistemicStatus(str, Enum):
    OBSERVATION = 'observation'
    HYPOTHESIS = 'hypothesis'
    VALIDATED = 'validated'
    REJECTED = 'rejected'


@dataclass(frozen=True)
class SemanticStatement:
    statement_id: str
    subject: str
    predicate: str
    object: str
    status: EpistemicStatus
    confidence: float
    provenance: tuple[str, ...] = ()
    validations: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple[str, str, str]:
        return (self.subject.lower(), self.predicate.lower(), self.object.lower())


class SemanticKnowledgeBase:
    def __init__(self, db_file: str | Path, validation_threshold: int = 2):
        if validation_threshold < 1:
            raise ValueError('validation_threshold must be positive')
        self.db_file = str(db_file)
        self.validation_threshold = validation_threshold
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS semantic_statements (
                statement_id TEXT PRIMARY KEY, subject TEXT NOT NULL, predicate TEXT NOT NULL,
                object TEXT NOT NULL, status TEXT NOT NULL, confidence REAL NOT NULL,
                provenance TEXT NOT NULL, validations TEXT NOT NULL, contradictions TEXT NOT NULL,
                metadata TEXT NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS semantic_promotion_audit (
                event_id TEXT PRIMARY KEY, statement_id TEXT NOT NULL, action TEXT NOT NULL,
                actor TEXT NOT NULL, previous_status TEXT NOT NULL, new_status TEXT NOT NULL,
                payload TEXT NOT NULL, created_at REAL NOT NULL)""")

    def _memory_metadata(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        result = dict(metadata or {})
        memory = dict(result.get('_memory', {}))
        now = time.time()
        memory.setdefault('created_at', now)
        memory.setdefault('last_recalled_at', now)
        memory.setdefault('recall_count', 0)
        memory.setdefault('independent_support', 0)
        memory.setdefault('utility', 0.0)
        result['_memory'] = memory
        return result

    def observe(self, subject: str, predicate: str, object: str, source: str, confidence: float = 0.5, metadata: dict[str, Any] | None = None) -> SemanticStatement:
        if not all(isinstance(value, str) and value.strip() for value in (subject, predicate, object, source)):
            raise ValueError('subject, predicate, object and source must be non-empty')
        if not 0.0 <= confidence <= 1.0:
            raise ValueError('confidence must be between 0 and 1')
        statement = SemanticStatement(str(uuid.uuid4()), subject.strip(), predicate.strip(), object.strip(), EpistemicStatus.OBSERVATION, confidence, (source,), (), (), self._memory_metadata(metadata))
        self._save(statement)
        return statement

    def hypothesize(self, subject: str, predicate: str, object: str, source: str, confidence: float = 0.5, metadata: dict[str, Any] | None = None) -> SemanticStatement:
        if not all(isinstance(value, str) and value.strip() for value in (subject, predicate, object, source)):
            raise ValueError('subject, predicate, object and source must be non-empty')
        if not 0.0 <= confidence <= 1.0:
            raise ValueError('confidence must be between 0 and 1')
        statement = SemanticStatement(str(uuid.uuid4()), subject.strip(), predicate.strip(), object.strip(), EpistemicStatus.HYPOTHESIS, confidence, (source,), (), (), self._memory_metadata(metadata))
        self._save(statement)
        return statement

    def _load(self, statement_id: str) -> SemanticStatement:
        with sqlite3.connect(self.db_file) as conn:
            row = conn.execute('SELECT * FROM semantic_statements WHERE statement_id = ?', (statement_id,)).fetchone()
        if row is None:
            raise KeyError(statement_id)
        return SemanticStatement(row[0], row[1], row[2], row[3], EpistemicStatus(row[4]), row[5], tuple(json.loads(row[6])), tuple(json.loads(row[7])), tuple(json.loads(row[8])), json.loads(row[9]))

    def _save(self, statement: SemanticStatement) -> None:
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT OR REPLACE INTO semantic_statements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (statement.statement_id, statement.subject, statement.predicate, statement.object, statement.status.value, statement.confidence, json.dumps(statement.provenance), json.dumps(statement.validations), json.dumps(statement.contradictions), json.dumps(statement.metadata, ensure_ascii=False)))

    def validate(self, statement_id: str, validator: str) -> SemanticStatement:
        statement = self._load(statement_id)
        if not validator.strip():
            raise ValueError('validator must be non-empty')
        validations = tuple(dict.fromkeys((*statement.validations, validator.strip())))
        status = EpistemicStatus.VALIDATED if len(validations) >= self.validation_threshold else EpistemicStatus.HYPOTHESIS
        updated = SemanticStatement(statement.statement_id, statement.subject, statement.predicate, statement.object, status, statement.confidence, statement.provenance, validations, statement.contradictions, statement.metadata)
        self._save(updated)
        return updated

    def contradict(self, statement_id: str, source: str) -> SemanticStatement:
        statement = self._load(statement_id)
        contradictions = tuple(dict.fromkeys((*statement.contradictions, source)))
        updated = SemanticStatement(statement.statement_id, statement.subject, statement.predicate, statement.object, EpistemicStatus.HYPOTHESIS, min(statement.confidence, 0.5), statement.provenance, statement.validations, contradictions, statement.metadata)
        self._save(updated)
        return updated

    def get(self, statement_id: str) -> SemanticStatement:
        return self._load(statement_id)

    def recall(self, statement_id: str, utility: float = 0.1) -> SemanticStatement:
        statement = self._load(statement_id)
        memory = dict(statement.metadata.get('_memory', {}))
        memory['last_recalled_at'] = time.time()
        memory['recall_count'] = int(memory.get('recall_count', 0)) + 1
        memory['utility'] = min(1.0, float(memory.get('utility', 0.0)) + max(0.0, utility))
        metadata = dict(statement.metadata)
        metadata['_memory'] = memory
        updated = SemanticStatement(statement.statement_id, statement.subject, statement.predicate, statement.object, statement.status, statement.confidence, statement.provenance, statement.validations, statement.contradictions, metadata)
        self._save(updated)
        return updated

    def add_independent_support(self, statement_id: str, source: str, support_kind: str = 'external') -> SemanticStatement:
        statement = self._load(statement_id)
        if not source.strip():
            raise ValueError('source must be non-empty')
        memory = dict(statement.metadata.get('_memory', {}))
        supports = set(memory.get('support_sources', []))
        supports.add(source.strip())
        memory['support_sources'] = sorted(supports)
        memory['independent_support'] = len(supports)
        metadata = dict(statement.metadata)
        metadata['_memory'] = memory
        updated = SemanticStatement(statement.statement_id, statement.subject, statement.predicate, statement.object, statement.status, statement.confidence, statement.provenance, statement.validations, statement.contradictions, metadata)
        self._save(updated)
        return updated

    def promote(self, statement_id: str, validator: str, minimum_support: int = 2, evidence_profiles: Iterable[SourceProfile] | None = None, evidence_quality: float = 1.0) -> SemanticStatement:
        statement = self._load(statement_id)
        if statement.status == EpistemicStatus.VALIDATED:
            return statement
        if statement.status != EpistemicStatus.HYPOTHESIS:
            raise ValueError('only hypotheses can be promoted')
        if statement.contradictions:
            raise ValueError('contradicted hypotheses cannot be promoted')
        support = int(statement.metadata.get('_memory', {}).get('independent_support', 0))
        if support < minimum_support:
            raise ValueError('insufficient independent support for promotion')
        assessment = None
        if evidence_profiles is not None:
            assessment = assess_evidence(evidence_profiles, evidence_quality=evidence_quality, minimum_families=2)
            if not assessment.promotable:
                raise ValueError(f'evidence reputation gate failed: {assessment.reason}')
        if not validator.strip():
            raise ValueError('validator must be non-empty')
        previous = statement.status
        promoted = self.validate(statement_id, validator.strip())
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT INTO semantic_promotion_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (str(uuid.uuid4()), statement_id, 'promote', validator.strip(), previous.value, promoted.status.value, json.dumps({'support': support, 'evidence_assessment': assessment.__dict__ if assessment else None}, ensure_ascii=False), time.time()))
        return promoted

    def rollback_promotion(self, statement_id: str, actor: str) -> SemanticStatement:
        statement = self._load(statement_id)
        if statement.status != EpistemicStatus.VALIDATED:
            raise ValueError('statement is not validated')
        downgraded = SemanticStatement(statement.statement_id, statement.subject, statement.predicate, statement.object, EpistemicStatus.HYPOTHESIS, statement.confidence, statement.provenance, statement.validations, statement.contradictions, statement.metadata)
        self._save(downgraded)
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT INTO semantic_promotion_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (str(uuid.uuid4()), statement_id, 'rollback', actor.strip(), statement.status.value, downgraded.status.value, '{}', time.time()))
        return downgraded

    def retention_score(self, statement: SemanticStatement, now: float | None = None) -> float:
        if statement.status == EpistemicStatus.VALIDATED:
            return 1.0
        memory = statement.metadata.get('_memory', {})
        now = time.time() if now is None else now
        age_days = max(0.0, (now - float(memory.get('last_recalled_at', now))) / 86400.0)
        recency = 2.71828 ** (-age_days / (14.0 if statement.status == EpistemicStatus.OBSERVATION else 30.0))
        recall = min(1.0, float(memory.get('recall_count', 0)) / 3.0)
        support = min(1.0, float(memory.get('independent_support', 0)) / 2.0)
        contradiction_penalty = min(0.8, 0.2 * len(statement.contradictions))
        return max(0.0, min(1.0, 0.35 * statement.confidence + 0.25 * recency + 0.20 * recall + 0.20 * support - contradiction_penalty))

    def evaporate(self, threshold: float = 0.18, now: float | None = None) -> list[str]:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError('threshold must be between 0 and 1')
        now = time.time() if now is None else now
        with sqlite3.connect(self.db_file) as conn:
            ids = [row[0] for row in conn.execute("SELECT statement_id FROM semantic_statements WHERE status != 'validated'").fetchall()]
        removed = []
        for statement_id in ids:
            statement = self._load(statement_id)
            if self.retention_score(statement, now) < threshold:
                with sqlite3.connect(self.db_file) as conn:
                    conn.execute('DELETE FROM semantic_statements WHERE statement_id = ?', (statement_id,))
                removed.append(statement_id)
        return removed

    def search(self, term: str, validated_only: bool = False) -> list[SemanticStatement]:
        with sqlite3.connect(self.db_file) as conn:
            if validated_only:
                rows = conn.execute("SELECT statement_id FROM semantic_statements WHERE status = 'validated' AND (subject LIKE ? OR predicate LIKE ? OR object LIKE ?)", tuple(f'%{term}%' for _ in range(3))).fetchall()
            else:
                rows = conn.execute("SELECT statement_id FROM semantic_statements WHERE subject LIKE ? OR predicate LIKE ? OR object LIKE ?", tuple(f'%{term}%' for _ in range(3))).fetchall()
        return [self._load(row[0]) for row in rows]
