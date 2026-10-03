"""Local shadow execution for isolated graph and knowledge experiments."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Callable

from .semantic_knowledge import SemanticKnowledgeBase


@dataclass(frozen=True)
class ShadowResult:
    status: str
    stable_hash_before: str
    stable_hash_after: str
    candidate_hash: str
    candidate_output: dict[str, Any]
    stable_unchanged: bool
    reason: str


class GraphSnapshot:
    def __init__(self, source: str | Path):
        self.source = Path(source)

    def digest(self, path: str | Path | None = None) -> str:
        target = Path(path) if path else self.source
        return hashlib.sha256(target.read_bytes()).hexdigest()

    def copy_to(self, target: str | Path) -> Path:
        destination = Path(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.source, destination)
        return destination


class ShadowCycle:
    def __init__(self, stable_graph_db: str | Path):
        self.snapshot = GraphSnapshot(stable_graph_db)

    def run(self, candidate: Callable[[Path], dict[str, Any]]) -> ShadowResult:
        stable_before = self.snapshot.digest()
        with tempfile.TemporaryDirectory(prefix='grandnexus-shadow-') as tmp:
            candidate_db = self.snapshot.copy_to(Path(tmp) / self.snapshot.source.name)
            try:
                output = candidate(candidate_db)
                if not isinstance(output, dict):
                    raise TypeError('candidate must return a dict')
                status = 'completed'
                reason = 'candidate executed on isolated graph copy'
            except Exception as exc:
                output = {'error_type': type(exc).__name__, 'error': str(exc)}
                status = 'failed'
                reason = 'candidate failed in isolated branch'
            candidate_hash = self.snapshot.digest(candidate_db)
        stable_after = self.snapshot.digest()
        return ShadowResult(status, stable_before, stable_after, candidate_hash, output, stable_before == stable_after, reason)

    def run_with_memory(self, candidate: Callable[[Path, SemanticKnowledgeBase], dict[str, Any]], evaporation_threshold: float = 0.18) -> ShadowResult:
        stable_before = self.snapshot.digest()
        with tempfile.TemporaryDirectory(prefix='grandnexus-shadow-') as tmp:
            tmp_path = Path(tmp)
            candidate_db = self.snapshot.copy_to(tmp_path / self.snapshot.source.name)
            memory = SemanticKnowledgeBase(tmp_path / 'candidate_memory.db')
            try:
                output = candidate(candidate_db, memory)
                if not isinstance(output, dict):
                    raise TypeError('candidate must return a dict')
                evaporated = memory.evaporate(evaporation_threshold)
                output = dict(output)
                output['memory_evaporated_count'] = len(evaporated)
                output['memory_survivor_count'] = len(memory.search(''))
                status = 'completed'
                reason = 'candidate executed with isolated temporary memory'
            except Exception as exc:
                output = {'error_type': type(exc).__name__, 'error': str(exc)}
                status = 'failed'
                reason = 'candidate failed in isolated branch'
            candidate_hash = self.snapshot.digest(candidate_db)
        stable_after = self.snapshot.digest()
        return ShadowResult(status, stable_before, stable_after, candidate_hash, output, stable_before == stable_after, reason)

    def export(self, result: ShadowResult, path: str | Path) -> None:
        Path(path).write_text(json.dumps({
            'status': result.status,
            'stable_hash_before': result.stable_hash_before,
            'stable_hash_after': result.stable_hash_after,
            'candidate_hash': result.candidate_hash,
            'candidate_output': result.candidate_output,
            'stable_unchanged': result.stable_unchanged,
            'reason': result.reason,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
