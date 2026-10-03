from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.pipeline import LightCognitivePipeline


class Noop:
    def start(self):
        return True
    def stop(self):
        return True


with tempfile.TemporaryDirectory() as tmp:
    core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / 'nexus.db'))
    core.register_module('broken', Noop(), dependencies=['missing'])
    assert core.start() is True
    assert core.running is True
    assert core.stop() is True
    assert core.running is False
    pipeline = LightCognitivePipeline(core)
    for bad in ('', '   ', None, 123):
        try:
            pipeline.process(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f'invalid input accepted: {bad!r}')
print('resilience=OK')
