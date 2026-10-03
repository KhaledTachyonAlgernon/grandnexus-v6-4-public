from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.problem_solver import ProblemSolver
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    home = graph.add_node('home')
    key = graph.add_node('key')
    door = graph.add_node('door')
    graph.relate(home, 'has', key, status=GraphStatus.VALIDATED, confidence=1.0, provenance=('test',))
    graph.relate(door, 'is', 'closed', status=GraphStatus.VALIDATED, confidence=1.0, provenance=('test',))
    actions = [
        SimAction('find_key', {f'has:{key.node_id}'}, {f'has_key:{key.node_id}'}),
        SimAction('open_door', {f'has_key:{key.node_id}'}, {f'door_open:{door.node_id}'}),
    ]
    solver = ProblemSolver(graph, actions)
    understanding = solver.understand(home.node_id, f'has_key:{key.node_id}')
    assert understanding.validated_relations
    solution = solver.solve(home.node_id, f'has_key:{key.node_id}')
    assert solution.status == 'solved' and solution.simulation and solution.simulation.success
    impossible = solver.solve(home.node_id, 'unknown:place')
    assert impossible.status == 'unresolved'
print('problem_solver=OK')
