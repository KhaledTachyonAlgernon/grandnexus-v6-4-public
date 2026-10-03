from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.semantic_graph_bridge import SemanticGraphBridge
from grandnexus.semantic_knowledge import SemanticKnowledgeBase

with tempfile.TemporaryDirectory() as tmp:
    kb = SemanticKnowledgeBase(Path(tmp) / 'knowledge.db')
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    bridge = SemanticGraphBridge(graph)
    statement = kb.observe('A', 'is', 'animal', 'vision:sim', 0.8)
    source, target, relation = bridge.project(statement)
    assert relation.status == GraphStatus.OBSERVATION
    assert relation.provenance == ('vision:sim',)
    assert graph.neighbors(source)[0].target_id == target.node_id
    kb.validate(statement.statement_id, 'reasoner')
    validated = kb.validate(statement.statement_id, 'reviewer')
    _, _, promoted = bridge.project(validated)
    assert promoted.status == GraphStatus.VALIDATED
print('semantic_graph_bridge=OK')
