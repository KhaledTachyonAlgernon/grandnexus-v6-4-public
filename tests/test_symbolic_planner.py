from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.symbolic_planner import SimAction, SymbolicPlanner

planner = SymbolicPlanner([
    SimAction('find_key', frozenset({'at_home'}), frozenset({'has_key'})),
    SimAction('open_door', frozenset({'has_key'}), frozenset({'door_open'}), risk='medium'),
])
plan = planner.plan('door_open', {'at_home'}, request_id='req-1')
assert plan.confidence == 1.0
assert [step.step_id for step in plan.steps] == ['find_key', 'open_door']
result = planner.simulate(plan, {'at_home'})
assert result.success and 'door_open' in result.final_state
bad_plan = planner.plan('door_open', {'outside'}, request_id='req-2')
assert bad_plan.confidence == 0.0 and bad_plan.steps == ()
print('symbolic_planner=OK')
