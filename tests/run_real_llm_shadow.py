from pathlib import Path
import json
import sys
import tempfile
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.llm_bridge import LLMBridge
from grandnexus.llm_shadow_cycle import LLMShadowCycle
from grandnexus.semantic_graph import SemanticGraph
from grandnexus.semantic_knowledge import SemanticKnowledgeBase

with tempfile.TemporaryDirectory() as tmp:
    graph_db = Path(tmp) / 'graph.db'
    memory_db = Path(tmp) / 'memory.db'
    SemanticGraph(graph_db).add_node('stable-root', node_id='root')
    SemanticKnowledgeBase(memory_db).observe('GrandNexus', 'has_component', 'memory', 'architecture-note', .95)
    cycle = LLMShadowCycle(graph_db, memory_db, LLMBridge(OpenAI(), model='gpt-5-mini'))
    result = cycle.run('GrandNexus utilise une mémoire sémantique et un graphe local. Extrais uniquement les relations explicitement affirmées.', source='real-llm-shadow')
    print(json.dumps({
        'status': result.status,
        'stable_graph_unchanged': result.stable_graph_unchanged,
        'stable_memory_unchanged': result.stable_memory_unchanged,
        'candidate_memory_count': result.candidate_memory_count,
        'candidates': list(result.candidates),
        'reason': result.reason,
    }, ensure_ascii=False, indent=2))
