from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.learning_controller import LearningController
from grandnexus.learning_experiment import SlowLearningStore
from grandnexus.llm_bridge import ExtractionCandidate
from grandnexus.llm_learning import IngestionResult
from grandnexus.llm_learning_controller import LLMProposalCoordinator
from grandnexus.metacognition_loop import MetacognitionLoop

with tempfile.TemporaryDirectory() as tmp:
    meta = MetacognitionLoop()
    store = SlowLearningStore(Path(tmp) / 'learning.db')
    controller = LearningController(meta, store, min_observations=3)
    coordinator = LLMProposalCoordinator(controller)
    candidate = ExtractionCandidate('agent', 'needs', 'key', 0.7, 'llm')
    ingestion = IngestionResult(candidate, 'hypothesis', 'statement-1', 'pending')
    for index in range(3):
        prediction = meta.register(0.7, {'case': index})
        meta.observe(prediction, True)
    proposal = coordinator.propose(ingestion, 'test hypothesis', {'kind': 'llm_rule'})
    assert proposal is not None and proposal.status == 'pending'
print('llm_learning_controller=OK')
