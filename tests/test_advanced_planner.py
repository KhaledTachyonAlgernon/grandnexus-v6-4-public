from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.advanced_planner import AdvancedPlanner
from grandnexus.symbolic_planner import SimAction

planner = AdvancedPlanner([
    SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
    SimAction('open_door', frozenset({'has:key'}), frozenset({'open:door'}), risk='medium'),
    SimAction('launch_real_robot', frozenset({'open:door'}), frozenset({'robot:active'}), risk='high'),
], max_risk='medium')

decision = planner.plan_compound(['open:door'], {'at:home'}, 'compound-1')
assert decision.accepted and decision.plan and len(decision.plan.steps) == 2
assert decision.risk == 'medium'
assert planner.planner.simulate(decision.plan, {'at:home'}).success

missing = planner.plan_compound(['unknown:goal'], {'at:home'})
assert not missing.accepted and 'not reachable' in missing.reason

blocked = planner.plan_compound(['robot:active'], {'at:home'})
assert not blocked.accepted and 'risk exceeds policy' in blocked.reason
print('advanced_planner=OK')
