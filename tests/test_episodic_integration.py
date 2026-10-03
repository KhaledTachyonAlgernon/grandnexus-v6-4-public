from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph = SemanticGraph(root / 'graph.db')
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('test',), 'v1')
        loop = IntegratedCognitiveLoop(graph, [
            SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
            SimAction('open_door', frozenset({'has:key'}), frozenset({'open:door'})),
            SimAction('inspect_room', frozenset({'open:door'}), frozenset({'room:inspected'})),
        ], root / 'learning.db', root / 'trace.db')
        first = loop.run('agent', ['open:door'], request_id='episode-1')
        second = loop.run('agent', ['room:inspected'], request_id='episode-2')
        unknown = loop.run('agent', ['launch:rocket'], expected_success=False, request_id='episode-3')
        assert first.accepted and first.simulation and first.simulation.success
        assert second.accepted and second.simulation and second.simulation.success
        assert second.simulation.executed == ('inspect_room',)
        assert 'open:door' in loop.episodic_context.recall(['room:inspected'], required_effects=['open:door'], current_state=['at:home']).recalled_state
        assert not unknown.accepted
        assert loop.episodic_context.size() == 3
        assert loop.learning.current().knowledge == {}
        print('episodic_integration=OK')


if __name__ == '__main__':
    main()
