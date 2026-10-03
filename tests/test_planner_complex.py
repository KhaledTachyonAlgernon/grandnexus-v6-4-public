from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.symbolic_planner import SimAction, SymbolicPlanner

# Multiple independent dependencies and a negative effect.
actions = [
    SimAction('unlock', frozenset({'has_key'}), frozenset({'door_open'}), frozenset({'door_locked'})),
    SimAction('get_key', frozenset({'at_home'}), frozenset({'has_key'})),
    SimAction('prepare', frozenset({'charged'}), frozenset({'ready'})),
]
planner = SymbolicPlanner(actions)
plan = planner.plan('door_open', {'at_home', 'door_locked', 'charged'})
assert [step.step_id for step in plan.steps] == ['get_key', 'unlock']
result = planner.simulate(plan, {'at_home', 'door_locked', 'charged'})
assert result.success and 'door_locked' not in result.final_state

# Cyclic preconditions must terminate without a plan.
cycle = SymbolicPlanner([
    SimAction('a', frozenset({'b'}), frozenset({'a'})),
    SimAction('b', frozenset({'a'}), frozenset({'b'})),
])
cycle_plan = cycle.plan('a', set())
assert not cycle_plan.steps and cycle_plan.confidence == 0.0

# Missing precondition and high-risk action remain visible to policy layers.
high = SymbolicPlanner([SimAction('danger', frozenset({'ready'}), frozenset({'done'}), risk='high')])
high_plan = high.plan('done', {'ready'})
assert high_plan.steps and high_plan.steps[0].risk == 'high'
missing = high.plan('done', set())
assert not missing.steps
print('planner_complex=OK')
