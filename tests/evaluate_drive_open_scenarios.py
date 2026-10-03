from pathlib import Path
import json
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
    scenarios = [
        {'name': 'explore_internal_model', 'external_effect': False, 'risk': 'low', 'reversible': True, 'contradiction': False, 'expected': 'progress_allowed'},
        {'name': 'ask_for_missing_knowledge', 'external_effect': False, 'risk': 'low', 'reversible': True, 'contradiction': False, 'expected': 'progress_allowed'},
        {'name': 'simulation_with_uncertain_outcome', 'external_effect': False, 'risk': 'medium', 'reversible': True, 'contradiction': False, 'expected': 'progress_allowed'},
        {'name': 'contradictory_open_world', 'external_effect': False, 'risk': 'low', 'reversible': True, 'contradiction': True, 'expected': 'verification_first'},
        {'name': 'high_risk_simulation', 'external_effect': False, 'risk': 'high', 'reversible': True, 'contradiction': False, 'expected': 'refused'},
        {'name': 'irreversible_medium_risk', 'external_effect': False, 'risk': 'medium', 'reversible': False, 'contradiction': False, 'expected': 'verification_first'},
        {'name': 'real_world_effect', 'external_effect': True, 'risk': 'low', 'reversible': True, 'contradiction': False, 'expected': 'refused'},
    ]
    signals = [DriveSignal('goal_progress', .9, .7, .6), DriveSignal('safety_check', .2, .2, .8)]
    results = []
    for scenario in scenarios:
        resolution = policy.resolve(signals, **{key: scenario[key] for key in ('external_effect', 'risk', 'reversible', 'contradiction')})
        result = dict(scenario)
        result.update({'actual': resolution.status, 'selected_drive': resolution.selected_drive, 'reason': resolution.reason, 'ranked': resolution.ranked})
        results.append(result)
    print(json.dumps(results, ensure_ascii=False, indent=2))
