from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.llm_bridge import ExtractionCandidate
from grandnexus.llm_learning import LLMLearningGate
from grandnexus.llm_verifier import LLMVerifier
from grandnexus.semantic_knowledge import SemanticKnowledgeBase

with tempfile.TemporaryDirectory() as tmp:
    kb = SemanticKnowledgeBase(Path(tmp) / 'knowledge.db', validation_threshold=2)
    known = kb.observe('door', 'is', 'open', 'sensor-a')
    kb.contradict(known.statement_id, 'sensor-b')
    candidates = [
        ExtractionCandidate('agent', 'needs', 'key', 0.7, 'llm'),
        ExtractionCandidate('door', 'is', 'open', 0.8, 'llm'),
    ]
    verified = LLMVerifier(kb).verify(candidates)
    ingested = LLMLearningGate(kb).ingest(candidates, verified)
    assert ingested[0].status == 'hypothesis' and ingested[0].statement_id
    assert ingested[1].status == 'rejected' and ingested[1].statement_id is None
    statement = kb.get(ingested[0].statement_id)
    assert statement.status.value == 'observation'
    assert len(statement.validations) == 0
print('llm_learning=OK')
