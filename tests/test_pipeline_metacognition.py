from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.metacognition_loop import MetacognitionLoop
from grandnexus.pipeline import LightCognitivePipeline

with tempfile.TemporaryDirectory() as tmp:
    core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / 'core.db'))
    meta = MetacognitionLoop()
    result = LightCognitivePipeline(core, metacognition=meta).process('Le système fonctionne.')
    assert result.prediction_id is not None
    assert meta.records[0].prediction_id == result.prediction_id
    meta.observe(result.prediction_id, True)
    review = meta.review()
    assert review.count == 1 and review.accuracy == 1.0
print('pipeline_metacognition=OK')
