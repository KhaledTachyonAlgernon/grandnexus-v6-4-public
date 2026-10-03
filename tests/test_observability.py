from pathlib import Path
import json
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.observability import TraceLog

with tempfile.TemporaryDirectory() as tmp:
    log = TraceLog(Path(tmp) / 'trace.db')
    cycle = 'cycle-1'
    log.record(cycle, 'retrieval', 'candidate_found', 'completed', 0.82, ('graph:r1',), {'source': 'hybrid'})
    log.record(cycle, 'proof', 'proof_built', 'accepted', 0.91, ('rule:r2',), {'steps': 2})
    log.record(cycle, 'simulation', 'action_simulated', 'completed', 1.0, (), {'real_hardware': False})
    events = log.cycle(cycle)
    assert [event.stage for event in events] == ['retrieval', 'proof', 'simulation']
    exported = json.loads(log.export_cycle(cycle))
    assert exported[1]['provenance'] == ['rule:r2']
    assert exported[2]['payload']['real_hardware'] is False
print('observability=OK')
