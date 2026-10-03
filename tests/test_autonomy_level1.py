from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.autonomy_level1 import AutonomyLevelOne
from grandnexus.drive_module import DriveModule
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction


def build(root: Path):
    graph = SemanticGraph(root / 'graph.db')
    agent = graph.add_node('agent', node_id='agent')
    home = graph.add_node('home', node_id='home')
    graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('autonomy-test',), 'v1')
    actions = [
        SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
        SimAction('open_door', frozenset({'has:key'}), frozenset({'door:open'}), frozenset({'door:closed'})),
        SimAction('enter_room', frozenset({'at:home', 'door:open'}), frozenset({'at:room'}), frozenset({'at:home'})),
        SimAction('return_home', frozenset({'at:room'}), frozenset({'at:home'}), frozenset({'at:room'})),
    ]
    loop = IntegratedCognitiveLoop(graph, actions, root / 'learning.db', root / 'trace.db', root / 'world.db')
    autonomy = AutonomyLevelOne(loop, DriveModule(root / 'drives.db'), 'agent')
    return loop, autonomy


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        loop, autonomy = build(root)
        cycles = [autonomy.step(index) for index in range(1, 7)]
        assert cycles[0].objective == 'has:key' and cycles[0].accepted
        assert any(row.objective == 'door:open' and row.accepted for row in cycles)
        before_conflict = loop.world_state.snapshot('agent')
        loop.world_state.apply_transition('agent', {'door:closed'}, (), 'test-conflict')
        blocked = autonomy.step(7)
        assert blocked.status == 'verification_first' and blocked.objective is None
        loop.world_state.apply_transition('agent', (), {'door:closed'}, 'test-resolution')
        resumed = autonomy.step(8)
        assert resumed.status == 'progress_allowed'
        assert loop.learning.current().knowledge == {}
        proposals = [row.learning_proposal_id for row in cycles + [blocked, resumed] if row.learning_proposal_id]
        print({'cycles': len(cycles) + 2, 'blocked': blocked.status, 'resumed': resumed.status, 'proposals': len(proposals)})
        print('autonomy_level1=OK')


if __name__ == '__main__':
    main()
