from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.episodic_context import LocalEpisodicContext, EpisodicRecall
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction


class NullEpisodicContext:
    def recall(self, objectives, required_effects=(), current_state=(), max_results=8):
        return EpisodicRecall(frozenset(), (), 0)
    def record(self, *args, **kwargs):
        return 'null'
    def size(self):
        return 0


def build(root, use_memory):
    graph = SemanticGraph(root / ('graph_memory.db' if use_memory else 'graph_nomemory.db'))
    agent = graph.add_node('agent', node_id='agent')
    home = graph.add_node('home', node_id='home')
    graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('test',), 'v1')
    actions = [
        SimAction('find_token', frozenset({'at:home'}), frozenset({'has:token'})),
        SimAction('open_gate', frozenset({'has:token'}), frozenset({'gate:open'})),
    ]
    loop = IntegratedCognitiveLoop(graph, actions, root / ('learn_memory.db' if use_memory else 'learn_nomemory.db'), root / ('trace_memory.db' if use_memory else 'trace_nomemory.db'), enable_world_state=False)
    if not use_memory:
        loop.episodic_context = NullEpisodicContext()
    first = loop.run('agent', ['has:token'], request_id=('memory' if use_memory else 'nomemory') + '-first')
    # The original acquisition route becomes unavailable; only recalled context may bridge the next episode.
    loop.advanced_planner.planner.actions = tuple(a for a in loop.advanced_planner.planner.actions if a.name != 'find_token')
    loop.graph_planner.planner.actions = tuple(a for a in loop.graph_planner.planner.actions if a.name != 'find_token')
    second = loop.run('agent', ['gate:open'], request_id=('memory' if use_memory else 'nomemory') + '-second')
    return first, second, loop


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        no_first, no_second, no_loop = build(root, False)
        mem_first, mem_second, mem_loop = build(root, True)
        result = {
            'without_memory': {'first': no_first.accepted, 'second': no_second.accepted, 'reason': no_second.reason},
            'with_episodic_memory': {'first': mem_first.accepted, 'second': mem_second.accepted, 'executed': mem_second.simulation.executed if mem_second.simulation else (), 'episodes': mem_loop.episodic_context.size()},
        }
        print(result)
        assert no_first.accepted and not no_second.accepted
        assert mem_first.accepted and mem_second.accepted and mem_second.simulation.success
        print('episodic_comparison=OK')


if __name__ == '__main__':
    main()
