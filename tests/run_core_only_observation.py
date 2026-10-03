import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction


def sha(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path = root / 'graph.db'
        learning_path = root / 'learning.db'
        trace_path = root / 'trace.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('reviewer',), 'v1')
        graph_before = sha(graph_path)
        loop = IntegratedCognitiveLoop(graph, [
            SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
            SimAction('open_door', frozenset({'has:key'}), frozenset({'open:door'}), risk='medium'),
        ], learning_path, trace_path)
        scenarios = [
            ('reachable-1', ['open:door'], True),
            ('reachable-2', ['open:door'], True),
            ('reachable-3', ['open:door'], True),
            ('unreachable', ['launch:rocket'], False),
            ('prediction-mismatch', ['open:door'], False),
        ]
        rows = []
        for request_id, objectives, expected in scenarios:
            result = loop.run('agent', objectives, expected_success=expected, request_id=request_id)
            rows.append({'request_id': request_id, 'accepted': result.accepted, 'reason': result.reason, 'simulation_success': result.simulation.success if result.simulation else None, 'executed': result.simulation.executed if result.simulation else (), 'expected_success': expected})
        proposal = loop.propose_learning({'plan_bias': 'prefer_shortest'}, 'validated simulation outcomes support shorter plans')
        graph_after = sha(graph_path)
        review = loop.meta.review()
        rows.append({'learning_proposal': proposal is not None, 'learning_status': proposal.status if proposal else None, 'knowledge_after': loop.learning.current().knowledge})
        print(json.dumps({'scenarios': rows, 'metacognition': {'count': review.count, 'accuracy': review.accuracy, 'mean_confidence': review.mean_confidence}, 'graph_unchanged': graph_before == graph_after, 'graph_before': graph_before, 'graph_after': graph_after, 'trace_exists': trace_path.exists(), 'learning_exists': learning_path.exists(), 'modules_disabled': ['llm', 'embeddings', 'multiagent']}, ensure_ascii=False, indent=2))
        assert graph_before == graph_after
        assert proposal is not None and proposal.status == 'pending'
        assert loop.learning.current().knowledge == {}


if __name__ == '__main__':
    main()
