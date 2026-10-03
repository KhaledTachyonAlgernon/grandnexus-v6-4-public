from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.drive_module import DriveModule, DriveSignal

with tempfile.TemporaryDirectory() as tmp:
    module = DriveModule(Path(tmp) / 'drives.db')
    module.register_drive('knowledge_gap', weight=1.0)
    module.register_drive('safety_check', weight=2.0)
    module.register_drive('disabled', enabled=False)
    safety = module.propose(DriveSignal('safety_check', 0.8, 0.8, 0.2), 'inspect recent failure')
    knowledge = module.propose(DriveSignal('knowledge_gap', 0.8, 0.8, 0.2), 'seek missing fact')
    assert safety.priority > knowledge.priority
    assert safety.status == 'pending'
    assert 'planner' in safety.reason
    try:
        module.propose(DriveSignal('disabled', 1.0), 'should not run')
    except ValueError as exc:
        assert 'disabled' in str(exc)
    else:
        raise AssertionError('disabled drive accepted')
    ranked = module.ranked([DriveSignal('knowledge_gap', 0.5), DriveSignal('safety_check', 0.5)])
    assert ranked[0][0].drive == 'safety_check'
print('drive_module=OK')
