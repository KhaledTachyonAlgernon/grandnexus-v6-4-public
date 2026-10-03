from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.failure_events import FailureRegistry

registry = FailureRegistry()
refusal = registry.record('rejected_before_plan', 'contradictory graph state')
assert not refusal.counts_as_prediction_error and not refusal.permits_learning_proposal
safety = registry.record('safety_stop', 'simulator stopped')
assert not safety.counts_as_prediction_error
error = registry.record('prediction_error', 'expected success, observed failure', {'request_id': 'r1'})
assert error.counts_as_prediction_error
assert len(registry.by_category('prediction_error')) == 1
try:
    registry.record('simulation_failure', '   ')
except ValueError:
    pass
else:
    raise AssertionError('empty failure message accepted')
print('failure_events=OK')
