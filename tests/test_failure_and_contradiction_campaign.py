import hashlib
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.multiagent.experimental_group import AgentProposal, ExperimentalAgent, ExperimentalMultiAgentGroup
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.source_reputation import SourceProfile


def make_graph(path):
    g = SemanticGraph(path)
    agent = g.add_node('agent'); memory = g.add_node('semantic memory')
    system = g.add_node('system'); active = g.add_node('active'); stopped = g.add_node('stopped')
    g.relate(agent, 'uses', memory, GraphStatus.VALIDATED, 0.9, ('symbolic-checker',))
    g.relate(system, 'state', active, GraphStatus.VALIDATED, 0.9, ('sensor-a',))
    g.relate(system, 'state', stopped, GraphStatus.REJECTED, 0.8, ('safety-checker',))
    return g


def run(proposer, request, g):
    profiles = (SourceProfile('symbolic', 'symbolic', 0.8, confirmed=8), SourceProfile('human', 'human', 0.8, confirmed=8))
    return ExperimentalMultiAgentGroup(proposer=proposer, source_profiles=profiles, graph=g).run(request)


def main():
    request = CognitiveRequest('The agent uses semantic memory')
    failures = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, exc in [('timeout', TimeoutError('upstream timeout')), ('malformed', ValueError('invalid JSON')), ('quota', RuntimeError('LLM proposer call budget exhausted'))]:
            def broken(_request, error=exc):
                raise error
            path = Path(tmp) / f'{name}.db'
            result = run(ExperimentalAgent('llm', 'proposal', broken), request, make_graph(path))
            failures[name] = {'consensus': result.consensus, 'degraded_mode': result.degraded_mode, 'action_allowed': result.action_allowed}

        contradiction_path = Path(tmp) / 'contradiction.db'
        graph = make_graph(contradiction_path)
        opposite = AgentProposal('llm', 'The system is stopped', 0.95, ('LLM assertion',), False, 'claim-specific', 'none')
        contradiction = run(ExperimentalAgent('llm', 'proposal', lambda _r: opposite), CognitiveRequest('The system is active'), graph)
        contradiction_path_hash = hashlib.sha256(contradiction_path.read_bytes()).hexdigest()
        opposite_again = AgentProposal('llm', 'The system is active', 0.95, ('The system is active',), False, 'claim-specific', 'none')
        accepted = run(ExperimentalAgent('llm', 'proposal', lambda _r: opposite_again), CognitiveRequest('The system is active'), graph)
        print({'failures': failures, 'contradictory_claim': contradiction.consensus, 'contradictory_anchor': contradiction.graph_anchor.reason, 'validated_claim': accepted.consensus, 'stable_hash': contradiction_path_hash})
        assert all(item['degraded_mode'] for item in failures.values())
        assert all(item['consensus'] == 'candidate-supported' for item in failures.values())
        assert contradiction.consensus == 'candidate-rejected'
        assert accepted.consensus == 'candidate-supported'


if __name__ == '__main__':
    main()
