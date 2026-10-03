from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.graph_planner import GraphPlanner
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    agent = graph.add_node('agent', node_id='agent')
    home = graph.add_node('home', node_id='home')
    graph.relate(agent, 'at', home, GraphStatus.OBSERVATION, 0.8, ('sensor',))
    graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('reviewer',), 'v1')
    planner = GraphPlanner(graph, [
        SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
        SimAction('open_door', frozenset({'has:key'}), frozenset({'open:door'}), risk='medium'),
    ])
    context = planner.context_for('agent')
    assert context.state == frozenset({'at:home'})
    plan = planner.plan_from_context('open:door', context, 'req-graph')
    assert plan.confidence == 1.0
    result = planner.simulate(plan, context)
    assert result.success and 'open:door' in result.final_state
print('graph_planner=OK')
