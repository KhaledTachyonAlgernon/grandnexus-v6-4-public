"""Append-only structured observability for GrandNexus cycles."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from typing import Any
import uuid


@dataclass(frozen=True)
class TraceEvent:
    cycle_id: str
    stage: str
    event_type: str
    status: str
    confidence: float | None = None
    provenance: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TraceLog:
    def __init__(self, db_file: str | Path):
        self.db_file = str(db_file)
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS trace_events (
                event_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL, stage TEXT NOT NULL,
                event_type TEXT NOT NULL, status TEXT NOT NULL, confidence REAL,
                provenance TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL)''')

    def record(self, cycle_id: str, stage: str, event_type: str, status: str,
               confidence: float | None = None, provenance: tuple[str, ...] = (),
               payload: dict[str, Any] | None = None) -> TraceEvent:
        if not cycle_id.strip() or not stage.strip() or not event_type.strip():
            raise ValueError('cycle_id, stage and event_type must be non-empty')
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            raise ValueError('confidence must be between 0 and 1')
        event = TraceEvent(cycle_id, stage, event_type, status, confidence, provenance, payload or {})
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT INTO trace_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                         (event.event_id, event.cycle_id, event.stage, event.event_type,
                          event.status, event.confidence, json.dumps(event.provenance),
                          json.dumps(event.payload, ensure_ascii=False), event.created_at))
        return event

    def cycle(self, cycle_id: str) -> list[TraceEvent]:
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute('SELECT * FROM trace_events WHERE cycle_id = ? ORDER BY rowid', (cycle_id,)).fetchall()
        return [TraceEvent(row[1], row[2], row[3], row[4], row[5], tuple(json.loads(row[6])), json.loads(row[7]), row[0], row[8]) for row in rows]

    def export_cycle(self, cycle_id: str) -> str:
        return json.dumps([asdict(event) for event in self.cycle(cycle_id)], ensure_ascii=False, indent=2)
