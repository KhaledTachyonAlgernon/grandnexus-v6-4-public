from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class WorldStateSnapshot:
    context_id: str
    facts: frozenset[str]
    conflicts: tuple[tuple[str, str], ...]
    revision: int


class WorldStateLedger:
    """Persistent, versioned current-state ledger.

    Episodic memory records what happened; this ledger records what is currently
    active in a context. Every transition is append-only in `state_events`, while
    `current_state` is a rebuildable materialized view.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.db_path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self.incompatibilities: dict[str, set[str]] = {}
        for left, right in (
            ("door:open", "door:closed"),
            ("gate:open", "gate:closed"),
            ("system:active", "system:stopped"),
            ("object:present", "object:absent"),
        ):
            self.register_incompatibility(left, right)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS revisions (
                    revision INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    provenance TEXT NOT NULL,
                    source_episode TEXT,
                    kind TEXT NOT NULL,
                    parent_revision INTEGER
                );
                CREATE TABLE IF NOT EXISTS state_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    revision INTEGER NOT NULL,
                    context_id TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    source_episode TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY(revision) REFERENCES revisions(revision)
                );
                CREATE TABLE IF NOT EXISTS current_state (
                    context_id TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    conflicted INTEGER NOT NULL DEFAULT 0,
                    revision INTEGER NOT NULL,
                    provenance TEXT NOT NULL,
                    source_episode TEXT,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(context_id, fact)
                );
                CREATE TABLE IF NOT EXISTS conflict_log (
                    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    revision INTEGER NOT NULL,
                    context_id TEXT NOT NULL,
                    left_fact TEXT NOT NULL,
                    right_fact TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );
                """
            )

    def register_incompatibility(self, left: str, right: str) -> None:
        if left == right:
            return
        self.incompatibilities.setdefault(left, set()).add(right)
        self.incompatibilities.setdefault(right, set()).add(left)

    def _new_revision(self, context_id: str, provenance: str, source_episode: str | None, kind: str, parent_revision: int | None = None) -> int:
        cur = self._db.execute(
            "INSERT INTO revisions(context_id, created_at, provenance, source_episode, kind, parent_revision) VALUES (?, ?, ?, ?, ?, ?)",
            (context_id, time.time(), provenance, source_episode, kind, parent_revision),
        )
        return int(cur.lastrowid)

    def apply_transition(self, context_id: str, added: Iterable[str], removed: Iterable[str], provenance: str, source_episode: str | None = None) -> int:
        added_set = set(added)
        removed_set = set(removed)
        now = time.time()
        with self._lock, self._db:
            revision = self._new_revision(context_id, provenance, source_episode, "transition")
            for fact in sorted(removed_set):
                self._db.execute(
                    "INSERT INTO state_events(revision, context_id, fact, operation, provenance, source_episode, created_at) VALUES (?, ?, ?, 'remove', ?, ?, ?)",
                    (revision, context_id, fact, provenance, source_episode, now),
                )
                self._db.execute(
                    "UPDATE current_state SET active=0, conflicted=0, revision=?, provenance=?, source_episode=?, updated_at=? WHERE context_id=? AND fact=?",
                    (revision, provenance, source_episode, now, context_id, fact),
                )
                for incompatible in self.incompatibilities.get(fact, set()):
                    self._db.execute(
                        "UPDATE current_state SET conflicted=0 WHERE context_id=? AND fact=? AND active=1",
                        (context_id, incompatible),
                    )
                    self._db.execute(
                        "UPDATE conflict_log SET resolved=1 WHERE context_id=? AND resolved=0 AND ((left_fact=? AND right_fact=?) OR (left_fact=? AND right_fact=?))",
                        (context_id, fact, incompatible, incompatible, fact),
                    )

            for fact in sorted(added_set):
                active_conflicts = []
                for incompatible in self.incompatibilities.get(fact, set()):
                    row = self._db.execute(
                        "SELECT fact FROM current_state WHERE context_id=? AND fact=? AND active=1",
                        (context_id, incompatible),
                    ).fetchone()
                    if row is not None:
                        active_conflicts.append(incompatible)
                conflicted = 1 if active_conflicts else 0
                self._db.execute(
                    "INSERT INTO state_events(revision, context_id, fact, operation, provenance, source_episode, created_at) VALUES (?, ?, ?, 'add', ?, ?, ?)",
                    (revision, context_id, fact, provenance, source_episode, now),
                )
                self._db.execute(
                    "INSERT INTO current_state(context_id, fact, active, conflicted, revision, provenance, source_episode, updated_at) VALUES (?, ?, 1, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(context_id, fact) DO UPDATE SET active=1, conflicted=excluded.conflicted, revision=excluded.revision, provenance=excluded.provenance, source_episode=excluded.source_episode, updated_at=excluded.updated_at",
                    (context_id, fact, conflicted, revision, provenance, source_episode, now),
                )
                for incompatible in active_conflicts:
                    self._db.execute(
                        "UPDATE current_state SET conflicted=1 WHERE context_id=? AND fact=?",
                        (context_id, incompatible),
                    )
                    left, right = sorted((fact, incompatible))
                    self._db.execute(
                        "INSERT INTO conflict_log(revision, context_id, left_fact, right_fact, resolved, created_at) VALUES (?, ?, ?, ?, 0, ?)",
                        (revision, context_id, left, right, now),
                    )
            return revision

    def snapshot(self, context_id: str) -> WorldStateSnapshot:
        with self._lock:
            rows = self._db.execute(
                "SELECT fact, conflicted, revision FROM current_state WHERE context_id=? AND active=1",
                (context_id,),
            ).fetchall()
            facts = frozenset(row["fact"] for row in rows if not row["conflicted"])
            conflict_rows = self._db.execute(
                "SELECT left_fact, right_fact FROM conflict_log WHERE context_id=? AND resolved=0 ORDER BY conflict_id",
                (context_id,),
            ).fetchall()
            revision = max((int(row["revision"]) for row in rows), default=0)
            return WorldStateSnapshot(context_id, facts, tuple((row["left_fact"], row["right_fact"]) for row in conflict_rows), revision)

    def history(self, context_id: str) -> list[dict]:
        rows = self._db.execute(
            "SELECT revision, fact, operation, provenance, source_episode, created_at FROM state_events WHERE context_id=? ORDER BY event_id",
            (context_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _state_at_revision(self, context_id: str, revision: int) -> set[str]:
        rows = self._db.execute(
            "SELECT fact, operation FROM state_events WHERE context_id=? AND revision<=? ORDER BY event_id",
            (context_id, revision),
        ).fetchall()
        state: set[str] = set()
        for row in rows:
            if row["operation"] == "add":
                state.add(row["fact"])
            elif row["operation"] == "remove":
                state.discard(row["fact"])
        return state

    def rollback_to(self, context_id: str, target_revision: int, provenance: str = "rollback") -> int:
        target = self._state_at_revision(context_id, target_revision)
        current_rows = self._db.execute(
            "SELECT fact FROM current_state WHERE context_id=? AND active=1",
            (context_id,),
        ).fetchall()
        current = {row["fact"] for row in current_rows}
        return self.apply_transition(
            context_id,
            added=target - current,
            removed=current - target,
            provenance=provenance,
            source_episode=f"rollback:{target_revision}",
        )

    def close(self) -> None:
        self._db.close()
