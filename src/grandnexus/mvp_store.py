"""Small SQLite persistence layer for the GrandNexus MVP."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class MvpStore:
    def __init__(self, db_file: str | Path):
        self.db_file = str(db_file)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_file) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
                );
                CREATE TABLE IF NOT EXISTS concepts (
                    concept_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
                );
                CREATE TABLE IF NOT EXISTS traces (
                    task_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
                );
                """
            )

    def save_result(self, result: Any) -> None:
        with sqlite3.connect(self.db_file) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO episodes(episode_id, content, source) VALUES (?, ?, ?)",
                (result.episode.episode_id, result.episode.events[0].content, result.working_item.source),
            )
            conn.execute(
                "INSERT OR REPLACE INTO concepts(concept_id, name, source) VALUES (?, ?, ?)",
                (result.concept.concept_id, result.concept.name, result.concept.source),
            )
            payload = {
                "task_id": result.task_id,
                "trace": result.trace,
                "reasoning": result.reasoning.conclusions,
            }
            conn.execute(
                "INSERT OR REPLACE INTO traces(task_id, payload) VALUES (?, ?)",
                (result.task_id, json.dumps(payload, ensure_ascii=False)),
            )

    def get_trace(self, task_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_file) as conn:
            row = conn.execute("SELECT payload FROM traces WHERE task_id = ?", (task_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def count(self, table: str) -> int:
        if table not in {"episodes", "concepts", "traces"}:
            raise ValueError("unsupported table")
        with sqlite3.connect(self.db_file) as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
