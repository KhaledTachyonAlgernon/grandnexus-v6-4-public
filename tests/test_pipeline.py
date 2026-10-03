from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.pipeline import LightCognitivePipeline

with tempfile.TemporaryDirectory() as tmp:
    core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / 'nexus.db'))
    result = LightCognitivePipeline(core).process('Le système doit mémoriser cette information.')
    assert result.perception.parsed_data.startswith('Le système')
    assert result.episode.events[0].content == result.working_item.content
    assert result.concept.name == result.working_item.content
    assert result.reasoning.complete is True
    assert len(result.trace) == 5
print('pipeline_behavior=OK')
