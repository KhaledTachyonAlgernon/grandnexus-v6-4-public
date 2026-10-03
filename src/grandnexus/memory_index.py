"""Explainable, incremental memory index for the GrandNexus level-14 MVP."""
from __future__ import annotations

from dataclasses import dataclass
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .semantic_ranker import SemanticRanker


@dataclass(frozen=True)
class MemoryHit:
    memory_id: str
    content: str
    score: float
    kind: str


class ExplainableMemoryIndex:
    def __init__(self, db_file: str | Path, ranker: 'SemanticRanker | None' = None):
        self.db_file = str(db_file)
        self.ranker = ranker
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS memories (memory_id TEXT PRIMARY KEY, content TEXT NOT NULL, kind TEXT NOT NULL)")

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {token.lower() for token in re.findall(r"[\wÀ-ÿ]+", text) if len(token) > 2}

    def add(self, memory_id: str, content: str, kind: str = "fact") -> None:
        if not content or not content.strip():
            raise ValueError("content must be non-empty")
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("INSERT OR REPLACE INTO memories(memory_id, content, kind) VALUES (?, ?, ?)", (memory_id, content.strip(), kind))

    def search(self, query: str, limit: int = 10) -> list[MemoryHit]:
        query_terms = self._terms(query)
        if not query_terms:
            return []
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute("SELECT memory_id, content, kind FROM memories").fetchall()
        if self.ranker is not None:
            ranked = self.ranker.rank(query, [(memory_id, content) for memory_id, content, _ in rows], limit)
            kinds = {memory_id: kind for memory_id, _, kind in rows}
            return [MemoryHit(item.memory_id, item.content, item.score, kinds[item.memory_id]) for item in ranked]
        hits = []
        for memory_id, content, kind in rows:
            terms = self._terms(content)
            overlap = query_terms & terms
            if overlap:
                score = len(overlap) / len(query_terms)
                hits.append(MemoryHit(memory_id, content, score, kind))
        return sorted(hits, key=lambda hit: (-hit.score, hit.memory_id))[:limit]

    def count(self) -> int:
        with sqlite3.connect(self.db_file) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
