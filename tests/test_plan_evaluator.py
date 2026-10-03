from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitivePlan, PlanStep
from grandnexus.plan_evaluator import PlanEvaluator

low = CognitivePlan('a', (PlanStep('safe', 'safe', (), 'low'),), 0.9, True)
medium = CognitivePlan('b', (PlanStep('medium', 'medium', (), 'medium'),), 0.9, True)
high = CognitivePlan('c', (PlanStep('danger', 'danger', (), 'high'),), 1.0, True)
evaluator = PlanEvaluator()
selected = evaluator.select([low, medium, high], max_risk='medium')
assert selected.status == 'selected' and selected.selected == low
assert all(item.risk != 'high' for item in selected.ranked)
rejected = evaluator.select([high], max_risk='medium')
assert rejected.status == 'unresolved'
tie = evaluator.select([low, CognitivePlan('d', (PlanStep('safe2', 'safe2', (), 'low'),), 0.9, True)])
assert tie.status == 'clarification_required'
print('plan_evaluator=OK')
