from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.learning_controller import LearningController
from grandnexus.learning_experiment import SlowLearningStore
from grandnexus.metacognition_loop import MetacognitionLoop

with tempfile.TemporaryDirectory() as tmp:
    meta = MetacognitionLoop()
    store = SlowLearningStore(Path(tmp) / 'learning.db')
    controller = LearningController(meta, store, min_observations=3)
    assert controller.propose_if_ready({'x': 'y'}, 'not ready') is None
    ids = [meta.register(0.5) for _ in range(3)]
    for prediction_id in ids:
        meta.observe(prediction_id, True)
    proposal = controller.propose_if_ready({'x': 'y'}, 'verified change')
    assert proposal is not None and proposal.status == 'pending'
    assert store.current().version_id == 'v0'
print('learning_controller=OK')
