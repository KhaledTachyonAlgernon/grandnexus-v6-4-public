from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitivePlan, PlanStep
from grandnexus.plan_evaluator import PlanEvaluator
from grandnexus.plan_feedback import PlanFeedbackStore

with tempfile.TemporaryDirectory() as tmp:
    plan = CognitivePlan('selected-1', (PlanStep('safe', 'safe', (), 'low'),), 0.9, True)
    selection = PlanEvaluator().select([plan])
    store = PlanFeedbackStore(Path(tmp) / 'feedback.db')
    feedback = store.record(selection, True, {'done'}, ('goal',))
    assert feedback.recommendation == 'candidate_preference_only_after_regression_check'
    assert feedback.selected_cost == 1 and feedback.selected_risk == 'low'
    assert len(store.list()) == 1
    ambiguous = PlanEvaluator().select([plan, CognitivePlan('selected-2', (PlanStep('safe2', 'safe2', (), 'low'),), 0.9, True)])
    feedback2 = store.record(ambiguous, False)
    assert feedback2.recommendation == 'request_clarification'
print('plan_feedback=OK')
