from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.graph_search import GraphSemanticSearch
from grandnexus.semantic_graph import GraphStatus, SemanticGraph

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    a = graph.add_node('A', kind='entity')
    animal = graph.add_node('animal', kind='concept')
    graph.relate(a, 'is', animal, GraphStatus.OBSERVATION, 0.8, ('vision:sim',))
    graph.relate(a, 'is', animal, GraphStatus.VALIDATED, 0.95, ('reviewer',), 'v2')
    search = GraphSemanticSearch(graph)
    all_hits = search.search('animal')
    valid_hits = search.search('animal', validated_only=True)
    assert all_hits and valid_hits
    assert valid_hits[0].status == GraphStatus.VALIDATED
    assert valid_hits[0].provenance == ('reviewer',)
print('graph_search=OK')
