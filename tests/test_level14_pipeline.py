from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.memory_index import ExplainableMemoryIndex
from grandnexus.pipeline import LightCognitivePipeline
from grandnexus.symbolic_reasoner import Fact, Rule, SymbolicReasoner

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    core = NexusCore(enable_async_messaging=False, db_file=str(root / 'core.db'))
    index = ExplainableMemoryIndex(root / 'memory.db')
    reasoner = SymbolicReasoner([Fact('A', 'animal')], [Rule('animal', 'breathes', 'animal-breathes')])
    pipeline = LightCognitivePipeline(core, memory_index=index, symbolic_reasoner=reasoner)
    result = pipeline.process('A breathes', source='level14')
    assert result.symbolic is not None
    assert result.symbolic.status == 'proved'
    assert result.symbolic.proof[0].rule_id == 'animal-breathes'
    assert index.search('A breathes')[0].memory_id == result.episode.episode_id
    assert any(item['stage'] == 'symbolic_reasoning' for item in result.trace)
print('level14_pipeline=OK')
