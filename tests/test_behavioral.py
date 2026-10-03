from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.pipeline import LightCognitivePipeline


class DummyModule:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        return True

    def stop(self):
        self.stopped = True
        return True


with tempfile.TemporaryDirectory() as tmp:
    db = str(Path(tmp) / 'nexus.db')
    core = NexusCore(enable_async_messaging=False, db_file=db)
    module = DummyModule()
    core.register_module('dummy', module, config={'mode': 'test'})
    assert core.get_module('dummy') is module
    assert core.get_module_config('dummy') == {'mode': 'test'}
    assert core.start() is True
    assert module.started is True
    assert core.stop() is True
    assert module.stopped is True

    pipeline = LightCognitivePipeline(core)
    first = pipeline.process('alpha')
    second = pipeline.process('beta')
    assert first.task_id != second.task_id
    assert first.reasoning.complete and second.reasoning.complete
    assert [x['stage'] for x in first.trace] == [
        'perception', 'working_memory', 'episodic_memory', 'semantic_memory', 'reasoning'
    ]
    try:
        pipeline.process('   ')
    except ValueError:
        pass
    else:
        raise AssertionError('empty input must be rejected')

    reloaded = NexusCore(enable_async_messaging=False, db_file=db)
    assert 'dummy' in reloaded.list_modules()
    assert reloaded.get_module_config('dummy') == {'mode': 'test'}

print('behavioral_scenarios=OK')
