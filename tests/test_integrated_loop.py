from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.hardware_contracts import ActionRequest
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    agent = graph.add_node('agent', node_id='agent')
    home = graph.add_node('home', node_id='home')
    graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('reviewer',), 'v1')
    loop = IntegratedCognitiveLoop(graph, [
        SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
        SimAction('open_door', frozenset({'has:key'}), frozenset({'open:door'}), risk='medium'),
    ], Path(tmp) / 'learning.db')
    for index in range(3):
        result = loop.run('agent', ['open:door'], request_id=f'req-{index}')
        print(index, result, loop.episodic_context.recall(['open:door']))
        assert result.accepted and result.simulation and result.simulation.success
    review = loop.meta.review()
    assert review.count == 3 and review.accuracy == 1.0
    proposal = loop.propose_learning({'plan_bias': 'prefer_shortest'}, 'validated simulation outcomes support shorter plans')
    assert proposal is not None and proposal.status == 'pending'
    assert loop.learning.current().knowledge == {}
    print('integrated_loop=OK')
