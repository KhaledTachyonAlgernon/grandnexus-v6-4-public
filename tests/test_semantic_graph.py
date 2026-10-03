from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_graph import GraphStatus, SemanticGraph

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    a = graph.add_node('A', kind='entity')
    animal = graph.add_node('animal', kind='concept')
    observed = graph.relate(a, 'is', animal, GraphStatus.OBSERVATION, 0.8, ('vision:sim',))
    validated = graph.relate(a, 'is', animal, GraphStatus.VALIDATED, 0.95, ('reviewer',), 'v2')
    neighbors = graph.neighbors(a)
    assert len(neighbors) == 2
    assert len(graph.neighbors(a, validated_only=True)) == 1
    assert graph.neighbors(a, validated_only=True)[0].relation_id == validated.relation_id
    assert graph.validated_relations()[0].version == 'v2'
    assert observed.provenance == ('vision:sim',)
print('semantic_graph=OK')
