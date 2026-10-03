from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.hardware_contracts import PerceptionEvent
from grandnexus.memory_index import ExplainableMemoryIndex
from grandnexus.pipeline import LightCognitivePipeline

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    core = NexusCore(enable_async_messaging=False, db_file=str(root / 'core.db'))
    index = ExplainableMemoryIndex(root / 'memory.db')
    pipeline = LightCognitivePipeline(core, memory_index=index)
    event = PerceptionEvent('vision', {'description': 'un cercle rouge'}, 0.7, 'camera:sim')
    memory_id = pipeline.ingest_perception_event(event)
    hits = index.search('cercle rouge')
    assert hits and hits[0].memory_id == memory_id
    assert hits[0].kind == 'perception:vision'
try:
    LightCognitivePipeline(core).ingest_perception_event(event)
except RuntimeError:
    pass
else:
    raise AssertionError('ingestion without memory index accepted')
print('perception_ingestion=OK')
