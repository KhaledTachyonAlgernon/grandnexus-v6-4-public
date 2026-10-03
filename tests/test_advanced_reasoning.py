from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.pipeline import LightCognitivePipeline
from grandnexus.advanced_reasoning import AdvancedReasoner, AdvancedReasoningOutput


class BrokenBackend:
    name = 'broken'
    def reason(self, text):
        raise RuntimeError('simulated backend failure')


with tempfile.TemporaryDirectory() as tmp:
    core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / 'nexus.db'))
    basic = LightCognitivePipeline(core).process('Pourquoi ce système existe-t-il ?')
    advanced = LightCognitivePipeline(core, advanced_reasoner=AdvancedReasoner()).process('Pourquoi ce système existe-t-il ?')
    fallback = AdvancedReasoner(BrokenBackend()).reason('Pourquoi ce système existe-t-il ?')

    assert len(basic.reasoning.conclusions) == 1
    assert len(advanced.reasoning.conclusions) == 2
    assert advanced.trace[-1]['engine'] == 'heuristic-local'
    assert fallback.engine == 'heuristic-local'
    assert fallback.confidence > 0

print('advanced_reasoning=OK')
