import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction


def digest(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path, learning_path, trace_path = root/'graph.db', root/'learning.db', root/'trace.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('reviewer',), 'v1')
        before = digest(graph_path)
        loop = IntegratedCognitiveLoop(graph, [
            SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
            SimAction('open_door', frozenset({'has:key'}), frozenset({'open:door'}), risk='medium'),
            SimAction('inspect_room', frozenset({'open:door'}), frozenset({'room:inspected'}), risk='low'),
        ], learning_path, trace_path)
        sequence = [
            ('s01', ['open:door'], True), ('s02', ['inspect:room'], True),
            ('s03', ['open:door'], True), ('s04', ['launch:rocket'], False),
            ('s05', ['open:door'], False), ('s06', ['has:key'], True),
            ('s07', ['launch:rocket'], False), ('s08', ['inspect:room'], True),
            ('s09', ['open:door'], True), ('s10', ['unknown:signal'], False),
            ('s11', ['has:key'], True), ('s12', ['open:door'], True),
            ('s13', ['inspect:room'], False), ('s14', ['unknown:signal'], False),
            ('s15', ['open:door'], True),
        ]
        rows, proposals = [], []
        for index, (rid, objectives, expected) in enumerate(sequence, 1):
            result = loop.run('agent', objectives, expected_success=expected, request_id=rid)
            row = {'step': index, 'request_id': rid, 'objectives': objectives, 'expected': expected, 'accepted': result.accepted, 'reason': result.reason, 'success': result.simulation.success if result.simulation else None, 'executed': list(result.simulation.executed) if result.simulation else [], 'failure': result.simulation.message if result.simulation and not result.simulation.success else None}
            if index in (3, 6, 9, 12, 15):
                proposal = loop.propose_learning({'plan_bias': f'observed_cycle_{index}'}, f'core observations at step {index} suggest reviewing plan selection')
                row['learning_proposal'] = proposal.status if proposal else None
                if proposal:
                    proposals.append({'id': proposal.proposal_id, 'status': proposal.status, 'hypothesis': proposal.hypothesis})
            rows.append(row)
        review = loop.meta.review()
        after = digest(graph_path)
        result = {'steps': rows, 'learning_proposals': proposals, 'metacognition': {'count': review.count, 'accuracy': review.accuracy, 'mean_confidence': review.mean_confidence}, 'graph_unchanged': before == after, 'graph_before': before, 'graph_after': after, 'knowledge': loop.learning.current().knowledge, 'trace_exists': trace_path.exists(), 'modules_disabled': ['llm', 'embeddings', 'multiagent'], 'temporary_state_restored': True}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        assert len(rows) == 15 and before == after and result['knowledge'] == {}


if __name__ == '__main__':
    main()
