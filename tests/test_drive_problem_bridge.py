from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.drive_module import DriveModule, DriveSignal
from grandnexus.drive_problem_bridge import DriveProblemBridge

with tempfile.TemporaryDirectory() as tmp:
    drives = DriveModule(Path(tmp) / 'drives.db')
    drives.register_drive('knowledge_gap', 1.0)
    drives.register_drive('safety_check', 2.0)
    bridge = DriveProblemBridge(drives)
    decision = bridge.propose_highest(
        [DriveSignal('knowledge_gap', 0.9, 0.3, 0.2), DriveSignal('safety_check', 0.6, 0.9, 0.1)],
        {'knowledge_gap': 'seek missing fact', 'safety_check': 'inspect recent failure'},
    )
    assert decision.status == 'pending'
    assert decision.proposal is not None
    assert decision.proposal.drive == 'safety_check'
    missing = bridge.propose_highest([DriveSignal('knowledge_gap', 0.9)], {})
    assert missing.status == 'clarification_required'
print('drive_problem_bridge=OK')
