"""Versioned, explicit and reversible symbolic learning."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LearningProposal:
    proposal_id: str
    parent_version: str
    change: dict[str, Any]
    hypothesis: str
    created_at: str
    status: str = 'pending'


@dataclass(frozen=True)
class KnowledgeVersion:
    version_id: str
    parent_version: str | None
    knowledge: dict[str, Any]
    source_proposal: str | None
    created_at: str


class SlowLearningStore:
    def __init__(self, db_file: str | Path):
        self.db_file = str(db_file)
        with sqlite3.connect(self.db_file) as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge_versions (
                version_id TEXT PRIMARY KEY,
                parent_version TEXT,
                knowledge TEXT NOT NULL,
                source_proposal TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_proposals (
                proposal_id TEXT PRIMARY KEY,
                parent_version TEXT NOT NULL,
                change_json TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            );
            """)
            if conn.execute('SELECT COUNT(*) FROM knowledge_versions').fetchone()[0] == 0:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute('INSERT INTO knowledge_versions VALUES (?, ?, ?, ?, ?)', ('v0', None, '{}', None, now))

    def current(self) -> KnowledgeVersion:
        with sqlite3.connect(self.db_file) as conn:
            row = conn.execute('SELECT version_id, parent_version, knowledge, source_proposal, created_at FROM knowledge_versions ORDER BY rowid DESC LIMIT 1').fetchone()
        return KnowledgeVersion(row[0], row[1], json.loads(row[2]), row[3], row[4])

    def propose(self, change: dict[str, Any], hypothesis: str) -> LearningProposal:
        proposal = LearningProposal(str(uuid.uuid4()), self.current().version_id, change, hypothesis, datetime.now(timezone.utc).isoformat())
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT INTO learning_proposals VALUES (?, ?, ?, ?, ?, ?)', (proposal.proposal_id, proposal.parent_version, json.dumps(change, ensure_ascii=False), hypothesis, proposal.created_at, proposal.status))
        return proposal

    def accept(self, proposal_id: str) -> KnowledgeVersion:
        with sqlite3.connect(self.db_file) as conn:
            row = conn.execute('SELECT parent_version, change_json, status FROM learning_proposals WHERE proposal_id = ?', (proposal_id,)).fetchone()
            if row is None:
                raise KeyError(proposal_id)
            if row[2] != 'pending':
                raise ValueError(f'proposal is already {row[2]}')
            current = self.current()
            if row[0] != current.version_id:
                raise RuntimeError('proposal parent is no longer current')
            knowledge = dict(current.knowledge)
            knowledge.update(json.loads(row[1]))
            version = KnowledgeVersion('v' + str(int(current.version_id[1:]) + 1), current.version_id, knowledge, proposal_id, datetime.now(timezone.utc).isoformat())
            conn.execute('INSERT INTO knowledge_versions VALUES (?, ?, ?, ?, ?)', (version.version_id, version.parent_version, json.dumps(version.knowledge, ensure_ascii=False), version.source_proposal, version.created_at))
            conn.execute("UPDATE learning_proposals SET status = 'accepted' WHERE proposal_id = ?", (proposal_id,))
            return version

    def reject(self, proposal_id: str) -> None:
        with sqlite3.connect(self.db_file) as conn:
            updated = conn.execute("UPDATE learning_proposals SET status = 'rejected' WHERE proposal_id = ? AND status = 'pending'", (proposal_id,)).rowcount
            if updated != 1:
                raise KeyError(proposal_id)

    def rollback(self, version_id: str) -> KnowledgeVersion:
        with sqlite3.connect(self.db_file) as conn:
            row = conn.execute('SELECT version_id, parent_version, knowledge, source_proposal, created_at FROM knowledge_versions WHERE version_id = ?', (version_id,)).fetchone()
            if row is None:
                raise KeyError(version_id)
            current = self.current()
            now = datetime.now(timezone.utc).isoformat()
            rollback = KnowledgeVersion('v' + str(int(current.version_id[1:]) + 1), current.version_id, json.loads(row[2]), f'rollback:{version_id}', now)
            conn.execute('INSERT INTO knowledge_versions VALUES (?, ?, ?, ?, ?)', (rollback.version_id, rollback.parent_version, json.dumps(rollback.knowledge, ensure_ascii=False), rollback.source_proposal, rollback.created_at))
            return rollback
