import hashlib
import json
import time
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.multiagent.experimental_group import ExperimentalAgent, ExperimentalMultiAgentGroup
from grandnexus.multiagent.llm_proposer import LLMCallBudget, StructuredLLMProposer
from grandnexus.multiagent.experimental_group import default_proposer
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.source_reputation import SourceProfile

CASES = [
    ('validated-memory', 'The agent uses semantic memory'),
    ('observed-sensor', 'The agent detects audio signals'),
    ('unknown-domain', 'What is the weather on Mars?'),
    ('contradiction', 'The system is idle'),
    ('negative-action', 'The robot does not open the door'),
    ('ambiguous-evidence', 'The agent uses semantic memory but the evidence concerns the audio sensor'),
]


def make_graph(path):
    graph = SemanticGraph(path)
    agent = graph.add_node('agent'); memory = graph.add_node('semantic memory'); audio = graph.add_node('audio sensor')
    system = graph.add_node('system'); active = graph.add_node('active'); stopped = graph.add_node('stopped')
    robot = graph.add_node('robot'); door = graph.add_node('door')
    graph.relate(agent, 'uses', memory, GraphStatus.VALIDATED, 0.9, ('symbolic-checker',))
    graph.relate(agent, 'uses', audio, GraphStatus.OBSERVATION, 0.7, ('sensor-a',))
    graph.relate(system, 'state', active, GraphStatus.VALIDATED, 0.9, ('sensor-a',))
    graph.relate(system, 'state', stopped, GraphStatus.REJECTED, 0.8, ('safety-checker',))
    graph.relate(robot, 'opens', door, GraphStatus.VALIDATED, 0.9, ('simulator',))
    return graph


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def usage_dict(usage):
    if not usage:
        return {}
    return {name: getattr(usage, name, None) for name in ('prompt_tokens', 'completion_tokens', 'total_tokens')}


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        graph_path = Path(tmp) / 'stable.db'
        graph = make_graph(graph_path)
        before = digest(graph_path)
        profiles = (SourceProfile('symbolic', 'symbolic', 0.8, confirmed=8), SourceProfile('human', 'human', 0.8, confirmed=8))
        budget = LLMCallBudget(max_calls=len(CASES))
        proposer = StructuredLLMProposer(model='gpt-5-mini', budget=budget)
        for case_id, text in CASES:
            request = CognitiveRequest(text)
            start = time.perf_counter()
            error = None
            try:
                proposal = proposer.propose(request)
                latency_ms = round((time.perf_counter() - start) * 1000, 1)
                fixed_agent = ExperimentalAgent('llm-proposer', 'proposal', lambda _request, p=proposal: p)
                llm_result = ExperimentalMultiAgentGroup(proposer=fixed_agent, source_profiles=profiles, graph=graph).run(request)
                deterministic_proposal = default_proposer(request)
                deterministic_agent = ExperimentalAgent('proposer', 'proposal', lambda _request, p=deterministic_proposal: p)
                deterministic_result = ExperimentalMultiAgentGroup(proposer=deterministic_agent, source_profiles=profiles, graph=graph).run(request)
                rows.append({'id': case_id, 'text': text, 'latency_ms': latency_ms, 'llm_claim': proposal.claim, 'llm_confidence': proposal.confidence, 'llm_evidence_count': len(proposal.evidence), 'llm_consensus': llm_result.consensus, 'deterministic_consensus': deterministic_result.consensus, 'disagreement': llm_result.consensus != deterministic_result.consensus, 'warnings': llm_result.verification.payload['warnings'], 'graph_anchor': llm_result.graph_anchor.reason if llm_result.graph_anchor else None, 'usage': usage_dict(proposer.last_usage), 'simulation_only': llm_result.simulation_only, 'action_allowed': llm_result.action_allowed})
            except Exception as exc:
                latency_ms = round((time.perf_counter() - start) * 1000, 1)
                error = f'{type(exc).__name__}: {exc}'
                rows.append({'id': case_id, 'text': text, 'latency_ms': latency_ms, 'error': error, 'disagreement': True, 'simulation_only': True, 'action_allowed': False})
        after = digest(graph_path)
    successful = [row for row in rows if 'error' not in row]
    latencies = [row['latency_ms'] for row in successful]
    summary = {'cases': len(rows), 'successful_calls': len(successful), 'errors': len(rows) - len(successful), 'mean_latency_ms': round(sum(latencies) / len(latencies), 1) if latencies else None, 'p50_latency_ms': sorted(latencies)[len(latencies) // 2] if latencies else None, 'disagreements': sum(row.get('disagreement', False) for row in rows), 'disagreement_rate': round(sum(row.get('disagreement', False) for row in rows) / len(rows), 3), 'external_actions_allowed': sum(row.get('action_allowed', False) for row in rows), 'non_simulation_results': sum(not row.get('simulation_only', True) for row in rows), 'stable_graph_unchanged': before == after, 'total_tokens': sum(row.get('usage', {}).get('total_tokens') or 0 for row in rows)}
    print(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
