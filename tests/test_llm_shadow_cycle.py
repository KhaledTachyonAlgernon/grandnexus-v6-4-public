from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.llm_bridge import LLMBridge
from grandnexus.llm_shadow_cycle import LLMShadowCycle
from grandnexus.semantic_graph import SemanticGraph
from grandnexus.semantic_knowledge import SemanticKnowledgeBase


class FakeClient:
    def create(self, **kwargs):
        class Message:
            content = '{"items":[{"subject":"door","predicate":"has_state","object":"closed","confidence":0.91}]}'
        class Choice:
            message = Message()
        class Response:
            choices = [Choice()]
        return Response()

with tempfile.TemporaryDirectory() as tmp:
    graph_db = Path(tmp) / 'graph.db'
    memory_db = Path(tmp) / 'memory.db'
    SemanticGraph(graph_db).add_node('stable', node_id='stable')
    SemanticKnowledgeBase(memory_db).observe('door', 'located_in', 'house', 'verified-source', .95)
    graph_before = graph_db.read_bytes()
    memory_before = memory_db.read_bytes()
    cycle = LLMShadowCycle(graph_db, memory_db, LLMBridge(FakeClient(), model='test-model'))
    result = cycle.run('The door is closed', source='test-llm')
    assert result.status == 'candidate_only'
    assert result.stable_graph_unchanged
    assert result.stable_memory_unchanged
    assert graph_db.read_bytes() == graph_before
    assert memory_db.read_bytes() == memory_before
    assert result.candidates[0]['status'] == 'hypothesis'
    assert result.candidate_memory_count == 2
print('llm_shadow_cycle=OK')
