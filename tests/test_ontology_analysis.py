from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.ontology_analysis import OntologyAnalyzer
from grandnexus.semantic_graph import GraphStatus, SemanticGraph

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    agent = graph.add_node('agent')
    home = graph.add_node('home')
    office = graph.add_node('office')
    graph.relate(agent, 'located_at', home, status=GraphStatus.VALIDATED, confidence=1.0, provenance=('a',))
    graph.relate(agent, 'located_at', office, status=GraphStatus.VALIDATED, confidence=0.9, provenance=('b',))
    view = OntologyAnalyzer(graph).view(agent.node_id)
    assert view.predicates == ('located_at',)
    assert 'located_at' in view.ambiguities
    assert len(view.relation_ids) == 2
print('ontology_analysis=OK')
