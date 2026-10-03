from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.memory.memory_manager import MemoryItem
from grandnexus.memory.working import WorkingMemoryItem
from grandnexus.cognition.cognition_manager import CognitionManager, CognitiveTask
from grandnexus.cognition.perception.perception_core import InputType, PerceptionResult
from grandnexus.cognition.reasoning.reasoning_core import ReasoningQuery

with tempfile.TemporaryDirectory() as tmp:
    core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / 'nexus.db'))
    item = MemoryItem(content='smoke', memory_id='m1')
    working = WorkingMemoryItem(item_id='w1', content='smoke', source='test')
    manager = CognitionManager(nexus_core=core)
    task = CognitiveTask(task_type='perception')
    result = PerceptionResult(input_type=InputType.TEXT, parsed_data='smoke')
    query = ReasoningQuery(question='smoke')
    assert item.content == working.content == result.parsed_data
    assert task.task_type == 'perception'
    assert query is not None and manager is not None
print('integration_light=OK')
