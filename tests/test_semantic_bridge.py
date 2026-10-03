from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.hardware_contracts import PerceptionEvent
from grandnexus.semantic_bridge import SemanticMemoryBridge
from grandnexus.semantic_knowledge import EpistemicStatus, SemanticKnowledgeBase

with tempfile.TemporaryDirectory() as tmp:
    kb = SemanticKnowledgeBase(Path(tmp) / 'semantic.db')
    bridge = SemanticMemoryBridge(kb)
    event = PerceptionEvent('vision', {'description': 'un animal'}, 0.9, 'camera:sim')
    statement = bridge.record_perception(event, 'A', 'is', 'animal')
    assert statement.status == EpistemicStatus.OBSERVATION
    assert bridge.validated_facts() == []
    bridge.knowledge_base.validate(statement.statement_id, 'reasoner')
    bridge.knowledge_base.validate(statement.statement_id, 'reviewer')
    facts = bridge.validated_facts('A')
    assert len(facts) == 1
    assert facts[0].subject == 'A'
print('semantic_bridge=OK')
