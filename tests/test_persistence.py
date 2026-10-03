from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.mvp_store import MvpStore
from grandnexus.pipeline import LightCognitivePipeline

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / 'mvp.db'
    core = NexusCore(enable_async_messaging=False, db_file=str(db))
    store = MvpStore(db)
    result = LightCognitivePipeline(core, store=store).process('information persistante')
    assert store.count('episodes') == 1
    assert store.count('concepts') == 1
    assert store.count('traces') == 1
    restored = MvpStore(db).get_trace(result.task_id)
    assert restored is not None
    assert restored['task_id'] == result.task_id
    assert restored['reasoning'][0]['confidence'] == 1.0
print('persistence=OK')
