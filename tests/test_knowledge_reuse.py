from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.learning_experiment import SlowLearningStore
from grandnexus.knowledge_reuse import ReusableKnowledge
from grandnexus.symbolic_reasoner import Fact

with tempfile.TemporaryDirectory() as tmp:
    store = SlowLearningStore(Path(tmp) / 'learning.db')
    proposal = store.propose({'animal': 'breathes'}, 'validated animal respiration rule')
    version = store.accept(proposal.proposal_id)
    knowledge = ReusableKnowledge(store)
    result = knowledge.reason([Fact('B', 'animal')], Fact('B', 'breathes'))
    assert result.outcome.status == 'proved'
    assert result.knowledge_version == version.version_id == 'v1'
    assert result.rules_loaded == 1
    assert result.outcome.proof[0].rule_id.startswith('v1:')
    exported = knowledge.export()
    assert exported['version'] == 'v1'
print('knowledge_reuse=OK')
