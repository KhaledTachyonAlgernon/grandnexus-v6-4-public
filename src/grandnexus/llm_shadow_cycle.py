"""Run LLM proposals in an isolated graph and epistemic-memory branch."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .llm_bridge import LLMBridge
from .semantic_knowledge import SemanticKnowledgeBase, EpistemicStatus


@dataclass(frozen=True)
class LLMShadowResult:
    status: str
    candidates: tuple[dict[str, Any], ...]
    stable_graph_unchanged: bool
    stable_memory_unchanged: bool
    candidate_graph_hash: str
    candidate_memory_count: int
    reason: str


class LLMShadowCycle:
    def __init__(self, stable_graph_db: str | Path, stable_memory_db: str | Path, bridge: LLMBridge):
        self.stable_graph_db = Path(stable_graph_db)
        self.stable_memory_db = Path(stable_memory_db)
        self.bridge = bridge

    @staticmethod
    def _digest(path: Path) -> str:
        import hashlib
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def run(self, text: str, source: str = 'llm-shadow') -> LLMShadowResult:
        graph_before = self._digest(self.stable_graph_db)
        memory_before = self._digest(self.stable_memory_db)
        with tempfile.TemporaryDirectory(prefix='grandnexus-llm-shadow-') as tmp:
            shadow_graph = Path(tmp) / self.stable_graph_db.name
            shadow_memory = Path(tmp) / self.stable_memory_db.name
            shutil.copy2(self.stable_graph_db, shadow_graph)
            shutil.copy2(self.stable_memory_db, shadow_memory)
            try:
                extracted = self.bridge.extract_candidates(text, source)
                memory = SemanticKnowledgeBase(shadow_memory)
                stored: list[dict[str, Any]] = []
                for candidate in extracted:
                    statement = memory.hypothesize(candidate.subject, candidate.predicate, candidate.object, candidate.source, candidate.confidence, {'origin': 'llm', 'shadow_only': True})
                    stored.append({'statement_id': statement.statement_id, 'subject': statement.subject, 'predicate': statement.predicate, 'object': statement.object, 'confidence': statement.confidence, 'status': statement.status.value, 'provenance': statement.provenance})
                status = 'candidate_only'
                reason = 'LLM proposals stored as shadow hypotheses; stable state untouched'
            except Exception as exc:
                stored = [{'error_type': type(exc).__name__, 'error': str(exc)}]
                status = 'failed'
                reason = 'LLM shadow execution failed in isolated branch'
            candidate_hash = self._digest(shadow_graph)
            candidate_memory_count = len(SemanticKnowledgeBase(shadow_memory).search('', validated_only=False))
        return LLMShadowResult(status, tuple(stored), graph_before == self._digest(self.stable_graph_db), memory_before == self._digest(self.stable_memory_db), candidate_hash, candidate_memory_count, reason)

    @staticmethod
    def export(result: LLMShadowResult, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding='utf-8')
