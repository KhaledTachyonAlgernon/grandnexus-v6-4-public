from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.drive_module import DriveModule, DriveSignal
from grandnexus.drive_policy import DrivePolicy

with tempfile.TemporaryDirectory() as tmp:
    drives = DriveModule(Path(tmp) / 'drives.db')
    drives.register_drive('goal_progress', 1.0)
    drives.register_drive('safety_check', 2.0)
    policy = DrivePolicy(drives)
    signals = [DriveSignal('goal_progress', .9, .8, .7), DriveSignal('safety_check', .2, .1, .8)]
    allowed = policy.resolve(signals, risk='low', reversible=True)
    assert allowed.status == 'progress_allowed'
    external = policy.resolve(signals, external_effect=True)
    assert external.status == 'approval_required' and external.selected_drive is None
    simulated_risk = policy.resolve(signals, risk='high', simulation_only=True)
    assert simulated_risk.status == 'simulation_allowed_with_review'
    refused_risk = policy.resolve(signals, risk='high', simulation_only=False)
    assert refused_risk.status == 'refused'
    verify = policy.resolve(signals, risk='medium', reversible=False)
    assert verify.status == 'verification_first'
    contradiction = policy.resolve(signals, contradiction=True)
    assert contradiction.status == 'verification_first'
print('drive_policy=OK')
