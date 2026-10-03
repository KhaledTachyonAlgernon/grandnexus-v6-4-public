from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.llm_bridge import ExtractionCandidate
from grandnexus.llm_verifier import LLMVerifier
from grandnexus.semantic_knowledge import SemanticKnowledgeBase

with tempfile.TemporaryDirectory() as tmp:
    kb = SemanticKnowledgeBase(Path(tmp) / 'knowledge.db', validation_threshold=1)
    supported = kb.observe('agent', 'needs', 'key', 'trusted-source', 0.9)
    kb.validate(supported.statement_id, 'validator-1')
    contradicted = kb.observe('door', 'is', 'open', 'sensor-a', 0.8)
    kb.contradict(contradicted.statement_id, 'sensor-b')
    candidates = [
        ExtractionCandidate('agent', 'needs', 'key', 0.95, 'llm'),
        ExtractionCandidate('agent', 'has', 'key', 0.95, 'llm'),
        ExtractionCandidate('door', 'is', 'open', 0.95, 'llm'),
    ]
    results = LLMVerifier(kb).verify(candidates)
    assert [item.status for item in results] == ['supported', 'unverified', 'contradicted']
    assert results[0].promotable and not results[1].promotable and not results[2].promotable
print('llm_verifier=OK')
