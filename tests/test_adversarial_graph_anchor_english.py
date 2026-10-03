import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.multiagent.experimental_group import ExperimentalMultiAgentGroup
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.source_reputation import SourceProfile

CASES = [
    ('novel-paraphrase', 'The agent makes use of its semantic memory', 'candidate-supported', 'validated'),
    ('near-relation', 'The agent uses episodic memory', 'candidate-unverified', 'none'),
    ('observed-paraphrase', 'The agent detects audio signals', 'candidate-unverified', 'observation'),
    ('partial-evidence', 'The agent uses semantic memory but the evidence concerns the audio sensor', 'candidate-unverified', 'validated'),
    ('nonlexical-contradiction', 'The system is idle', 'candidate-rejected', 'non-lexical-contradiction'),
    ('semantic-negation', 'The robot does not open the door', 'candidate-unverified', 'validated-negated'),
    ('unseen-relation', 'The Orion module reasons about memory', 'candidate-unverified', 'none'),
    ('safe-action-boundary', 'Prepare a command for simulation only', 'candidate-unverified', 'none'),
]


def make_graph(path):
    graph = SemanticGraph(path)
    agent = graph.add_node('agent')
    memory = graph.add_node('semantic memory')
    episodic = graph.add_node('episodic memory')
    audio = graph.add_node('audio sensor')
    system = graph.add_node('system')
    active = graph.add_node('active')
    stopped = graph.add_node('stopped')
    robot = graph.add_node('robot')
    door = graph.add_node('door')
    graph.relate(agent, 'uses', memory, GraphStatus.VALIDATED, 0.9, ('symbolic-checker',))
    graph.relate(agent, 'uses', episodic, GraphStatus.OBSERVATION, 0.7, ('sensor-a',))
    graph.relate(agent, 'uses', audio, GraphStatus.OBSERVATION, 0.7, ('sensor-a',))
    graph.relate(system, 'state', active, GraphStatus.VALIDATED, 0.9, ('sensor-a',))
    graph.relate(system, 'state', stopped, GraphStatus.REJECTED, 0.8, ('safety-checker',))
    graph.relate(robot, 'opens', door, GraphStatus.VALIDATED, 0.9, ('simulator',))
    return graph


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        graph_path = Path(tmp) / 'graph.db'
        graph = make_graph(graph_path)
        profiles = (SourceProfile('symbolic', 'symbolic', 0.8, confirmed=8), SourceProfile('human', 'human', 0.8, confirmed=8))
        group = ExperimentalMultiAgentGroup(source_profiles=profiles, graph=graph)
        before = digest(graph_path)
        rows = []
        for case_id, text, expected, category in CASES:
            result = group.run(CognitiveRequest(text))
            anchor = result.graph_anchor
            rows.append({'id': case_id, 'expected': expected, 'actual': result.consensus, 'correct': result.consensus == expected, 'category': category, 'matched_statuses': anchor.matched_statuses if anchor else (), 'reason': anchor.reason if anchor else None, 'warnings': result.verification.payload['warnings']})
        summary = {'cases': len(rows), 'correct': sum(row['correct'] for row in rows), 'accuracy': round(sum(row['correct'] for row in rows) / len(rows), 3), 'nonlexical_contradiction_missed': any(row['category'] == 'non-lexical-contradiction' and row['actual'] != row['expected'] for row in rows), 'negation_missed': any(row['category'] == 'validated-negated' and row['actual'] == 'candidate-supported' for row in rows), 'partial_evidence_supported': any(row['category'] == 'validated' and row['actual'] == 'candidate-supported' for row in rows), 'stable_graph_unchanged': before == digest(graph_path)}
        print(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
