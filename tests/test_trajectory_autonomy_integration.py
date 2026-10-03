import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from grandnexus.autonomy_level1 import AutonomyLevelOne
from grandnexus.drive_module import DriveModule
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def actions():
    return [
        SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
        SimAction('open_door', frozenset({'has:key'}), frozenset({'door:open'}), frozenset({'door:closed'})),
        SimAction('enter_room', frozenset({'at:home', 'door:open'}), frozenset({'at:room'}), frozenset({'at:home'})),
        SimAction('return_home', frozenset({'at:room'}), frozenset({'at:home'}), frozenset({'at:room'})),
        SimAction('close_door', frozenset({'at:home', 'door:open'}), frozenset({'door:closed'}), frozenset({'door:open'})),
    ]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path = root / 'graph.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('seed',), 'v1')
        graph_before = digest(graph_path)
        loop = IntegratedCognitiveLoop(graph, actions(), root / 'learning.db', root / 'trace.db', world_state_db=root / 'world.db')
        autonomy = AutonomyLevelOne(loop, DriveModule(root / 'drives.db'), 'agent')
        rows = [autonomy.step(cycle).to_dict() for cycle in range(1, 41)]
        reviews = [row for row in rows if row['status'] == 'trajectory_review']
        assert reviews, rows
        assert min(row['cycle'] for row in reviews) > 12
        assert all(row['trajectory_status'] == 'stagnating' for row in reviews)
        assert all(row['learning_proposal_id'] for row in reviews)
        first_review = reviews[0]['cycle']
        resumed = [row for row in rows if row['cycle'] > first_review and row['accepted']]
        assert resumed, rows
        assert graph_before == digest(graph_path)
        assert loop.learning.current().knowledge == {}
        print({'cycles': len(rows), 'trajectory_reviews': len(reviews), 'first_review': first_review, 'resumed_actions': len(resumed)})


if __name__ == '__main__':
    main()
