from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_knowledge import EpistemicStatus, SemanticKnowledgeBase

with tempfile.TemporaryDirectory() as tmp:
    kb = SemanticKnowledgeBase(Path(tmp) / 'semantic.db', validation_threshold=2)
    statement = kb.observe('A', 'is', 'animal', source='vision:sim', confidence=0.7)
    assert statement.status == EpistemicStatus.OBSERVATION
    first = kb.validate(statement.statement_id, 'reasoner:rule-check')
    assert first.status == EpistemicStatus.HYPOTHESIS
    second = kb.validate(statement.statement_id, 'human:review')
    assert second.status == EpistemicStatus.VALIDATED
    assert set(second.provenance) == {'vision:sim'}
    assert len(second.validations) == 2
    contradiction = kb.contradict(statement.statement_id, 'reasoner:conflict-check')
    assert contradiction.status == EpistemicStatus.HYPOTHESIS
    assert contradiction.confidence == 0.5
    assert kb.search('animal', validated_only=True) == []
    assert kb.search('animal')[0].status == EpistemicStatus.HYPOTHESIS
print('semantic_knowledge=OK')
