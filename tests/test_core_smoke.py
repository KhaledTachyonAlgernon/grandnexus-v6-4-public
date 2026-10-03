import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore

with tempfile.TemporaryDirectory() as tmp:
    core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / 'nexus.db'))
    assert core.running is False
    assert core.list_modules() == []
print('core_smoke=OK')
