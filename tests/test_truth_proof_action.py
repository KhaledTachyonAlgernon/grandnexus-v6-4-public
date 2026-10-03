from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.hardware_contracts import ActionRequest, PerceptionEvent
from grandnexus.robot_simulator import RobotSimulator
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_reasoner import Fact, Rule, SymbolicReasoner

# Pertinence/perception is not truth: an observation is excluded from validated facts.
event = PerceptionEvent('vision', {'label': 'animal'}, 0.95, 'camera:sim')
assert event.confidence == 0.95

# Truth/proof: only an explicit fact can support a proof.
reasoner = SymbolicReasoner([Fact('A', 'animal')], [Rule('animal', 'breathes')])
proved = reasoner.prove(Fact('A', 'breathes'))
assert proved.status == 'proved'
assert proved.proof and proved.proof[0].premises[0].predicate == 'animal'

# Action: a non-simulation request is rejected; an unsafe simulated move is rejected.
simulator = RobotSimulator(max_position=1.0)
real_result = simulator.execute(ActionRequest('move', {'position': 0.5}, simulation=False))
assert not real_result.accepted and not real_result.executed
unsafe_result = simulator.execute(ActionRequest('move', {'position': 5.0}, simulation=True))
assert not unsafe_result.accepted and not unsafe_result.executed
safe_result = simulator.execute(ActionRequest('move', {'position': 0.5}, simulation=True))
assert safe_result.accepted and safe_result.executed
print('truth_proof_action=OK')
