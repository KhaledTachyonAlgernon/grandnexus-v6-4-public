from dataclasses import asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import AgentMessage, CognitivePlan, CognitiveRequest, KnowledgeEnvelope, PlanStep

knowledge = KnowledgeEnvelope('A', 'is', 'animal', 'validated', 1.0, ('reasoner',), 'v1')
request = CognitiveRequest('plan a safe move', constraints=('simulation_only',))
step = PlanStep('s1', 'inspect state', risk='low')
plan = CognitivePlan(request.request_id, (step,), 0.8)
message = AgentMessage('planner', 'verifier', 'proposal', {'steps': 1})
assert asdict(knowledge)['status'] == 'validated'
assert asdict(plan)['simulation_only'] is True
assert message.message_type == 'proposal'
print('branch_contracts=OK')
