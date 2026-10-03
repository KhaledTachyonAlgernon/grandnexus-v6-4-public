from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.learning_experiment import SlowLearningStore

with tempfile.TemporaryDirectory() as tmp:
    store = SlowLearningStore(Path(tmp) / 'learning.db')
    assert store.current().version_id == 'v0'
    rejected = store.propose({'animal': 'breathes'}, 'test rejected proposal')
    store.reject(rejected.proposal_id)
    assert store.current().version_id == 'v0'
    accepted = store.propose({'animal': 'breathes'}, 'add verified rule')
    version = store.accept(accepted.proposal_id)
    assert version.version_id == 'v1'
    assert store.current().knowledge == {'animal': 'breathes'}
    second = store.propose({'plant': 'needs-light'}, 'add second verified rule')
    version2 = store.accept(second.proposal_id)
    assert version2.version_id == 'v2'
    rollback = store.rollback('v1')
    assert rollback.knowledge == {'animal': 'breathes'}
    assert store.current().version_id == 'v3'
print('slow_learning=OK')
