from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.advanced_planner import AdvancedPlanner
from grandnexus.graph_planner import GraphPlanner
from grandnexus.hardware_contracts import ActionRequest
from grandnexus.metacognition_loop import MetacognitionLoop
from grandnexus.robot_simulator import RobotSimulator
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    agent = graph.add_node('agent', node_id='agent')
    home = graph.add_node('home', node_id='home')
    away = graph.add_node('away', node_id='away')
    graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('reviewer-a',), 'v1')
    graph.relate(agent, 'at', away, GraphStatus.VALIDATED, 0.95, ('reviewer-b',), 'v2')
    graph_planner = GraphPlanner(graph, [SimAction('open', frozenset({'at:home'}), frozenset({'open:door'}))])
    context = graph_planner.context_for('agent')
    assert context.contradiction_relation_ids
    try:
        graph_planner.plan_from_context('open:door', context)
    except ValueError as exc:
        assert 'contradictory' in str(exc)
    else:
        raise AssertionError('contradiction was not blocked')

advanced = AdvancedPlanner([SimAction('danger', frozenset({'ready'}), frozenset({'done'}), risk='high')])
assert not advanced.plan_compound(['done'], {'ready'}).accepted

sim = RobotSimulator()
sim.stop()
assert not sim.execute(ActionRequest('move', {'position': 0.2})).accepted

meta = MetacognitionLoop()
prediction_id = meta.register(0.95, {'case': 'negative'})
meta.observe(prediction_id, False)
review = meta.review()
assert review.recommendation == 'reduce_confidence_or_request_verification'
print('negative_robustness=OK')
