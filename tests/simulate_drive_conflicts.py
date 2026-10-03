from pathlib import Path
import json
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.drive_module import DriveModule, DriveSignal
from grandnexus.drive_problem_bridge import DriveProblemBridge


def decide(safety: DriveSignal, progress: DriveSignal, external: bool, risk: str, reversible: bool, contradiction: bool):
    if external:
        return 'refused', 'external_effect_requires_explicit_hardware_policy'
    if contradiction:
        return 'verification_first', 'contradictory_signals_or_knowledge'
    if risk == 'high':
        return 'refused', 'risk_exceeds_default_policy'
    if safety.intensity >= 0.8 and not reversible:
        return 'verification_first', 'safety_signal_high_without_reversibility'
    if safety.intensity >= progress.intensity and safety.urgency >= progress.urgency:
        return 'safety_first', 'safety_priority'
    return 'progress_allowed', 'reversible_low_risk_simulation'

with tempfile.TemporaryDirectory() as tmp:
    drives = DriveModule(Path(tmp) / 'drives.db')
    drives.register_drive('goal_progress', 1.0)
    drives.register_drive('safety_check', 2.0)
    bridge = DriveProblemBridge(drives)
    cases = [
        ('safe_cognitive_progress', DriveSignal('safety_check', .1, .1, .9), DriveSignal('goal_progress', .9, .4, .7), False, 'low', True, False),
        ('contradiction', DriveSignal('safety_check', .9, .9, .2), DriveSignal('goal_progress', .9, .8, .7), False, 'low', True, True),
        ('high_risk_progress', DriveSignal('safety_check', .8, .8, .2), DriveSignal('goal_progress', 1.0, 1.0, .8), False, 'high', False, False),
        ('reversible_progress', DriveSignal('safety_check', .3, .2, .7), DriveSignal('goal_progress', .7, .5, .6), False, 'low', True, False),
        ('real_world_action', DriveSignal('safety_check', .4, .4, .5), DriveSignal('goal_progress', 1.0, 1.0, .6), True, 'low', True, False),
    ]
    results = []
    for name, safety, progress, external, risk, reversible, contradiction in cases:
        decision, reason = decide(safety, progress, external, risk, reversible, contradiction)
        mapping = {'safety_check': 'inspect and verify', 'goal_progress': 'advance simulated goal'}
        proposal = bridge.propose_highest([safety, progress], mapping)
        results.append({'name': name, 'decision': decision, 'reason': reason, 'top_drive': proposal.proposal.drive if proposal.proposal else None, 'proposal_status': proposal.status})
    print(json.dumps(results, ensure_ascii=False, indent=2))
