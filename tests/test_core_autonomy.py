from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.multiagent.experimental_group import AgentProposal, ExperimentalAgent, ExperimentalMultiAgentGroup, default_proposer
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.source_reputation import SourceProfile


def graph(path):
    g = SemanticGraph(path)
    a = g.add_node('agent'); m = g.add_node('semantic memory')
    g.relate(a, 'uses', m, GraphStatus.VALIDATED, 0.9, ('symbolic-checker',))
    return g


def run_with(agent, request, g):
    profiles = (SourceProfile('symbolic', 'symbolic', 0.8, confirmed=8), SourceProfile('human', 'human', 0.8, confirmed=8))
    return ExperimentalMultiAgentGroup(proposer=agent, source_profiles=profiles, graph=g).run(request)


def main():
    request = CognitiveRequest('The agent uses semantic memory')
    with tempfile.TemporaryDirectory() as tmp:
        baseline = default_proposer(request)
        baseline_result = run_with(ExperimentalAgent('proposer', 'proposal', lambda _r: baseline), request, graph(Path(tmp) / 'baseline.db'))
        unavailable = run_with(None, request, graph(Path(tmp) / 'unavailable.db'))
        assert baseline_result.consensus == 'candidate-supported'
        assert unavailable.consensus == 'candidate-supported'
        assert unavailable.degraded_mode is False

        def broken(_request):
            raise RuntimeError('LLM unavailable')
        failed = run_with(ExperimentalAgent('llm', 'proposal', broken), request, graph(Path(tmp) / 'failed.db'))
        assert failed.degraded_mode is True
        assert failed.consensus == 'candidate-supported'

        disagreement = AgentProposal('llm', 'The agent deletes semantic memory', 0.95, ('llm claim',), False, 'claim-specific', 'none')
        disagreement_result = run_with(ExperimentalAgent('llm', 'proposal', lambda _r: disagreement), request, graph(Path(tmp) / 'disagreement.db'))
        assert disagreement_result.consensus != 'candidate-supported'
        assert disagreement_result.degraded_mode is False
        print({'baseline': baseline_result.consensus, 'llm_absent': unavailable.consensus, 'llm_failed': failed.consensus, 'llm_disagrees': disagreement_result.consensus})


if __name__ == '__main__':
    main()
