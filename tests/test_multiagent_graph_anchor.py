from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.graph_anchor import assess_graph_anchor
from grandnexus.multiagent.experimental_group import ExperimentalMultiAgentGroup
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.source_reputation import SourceProfile


def build_graph(path):
    graph = SemanticGraph(path)
    agent = graph.add_node('agent')
    memory = graph.add_node('semantic memory')
    graph.relate(agent, 'uses', memory, GraphStatus.VALIDATED, 0.9, ('symbolic-checker',))
    return graph


def main():
    with tempfile.TemporaryDirectory() as tmp:
        graph = build_graph(Path(tmp) / 'graph.db')
        profiles = (SourceProfile('symbolic', 'symbolic', 0.8, confirmed=8), SourceProfile('human', 'human', 0.8, confirmed=8))
        group = ExperimentalMultiAgentGroup(source_profiles=profiles, graph=graph)
        supported = group.run(CognitiveRequest('L’agent utilise la mémoire sémantique'))
        assert supported.consensus == 'candidate-supported'
        assert supported.graph_anchor and supported.graph_anchor.validated_anchor

        unknown = group.run(CognitiveRequest('L’agent utilise une mémoire jamais observée'))
        assert unknown.consensus == 'candidate-unverified'
        assert unknown.graph_anchor and not unknown.graph_anchor.validated_anchor

        anchor = assess_graph_anchor(graph, 'L’agent utilise la mémoire sémantique')
        assert anchor.matched_provenance == ('symbolic-checker',)
        print({'validated_anchor': supported.consensus, 'missing_anchor': unknown.consensus, 'provenance': anchor.matched_provenance})


if __name__ == '__main__':
    main()
