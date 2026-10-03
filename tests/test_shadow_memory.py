from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.shadow_cycle import ShadowCycle
from grandnexus.semantic_knowledge import SemanticKnowledgeBase


def candidate(graph_db, memory: SemanticKnowledgeBase):
    memory.hypothesize('mars', 'has', 'weather tomorrow', 'llm-shadow', 0.3, {'_memory': {'last_recalled_at': 0}})
    useful = memory.hypothesize('agent', 'uses', 'semantic memory', 'llm-shadow', 0.7)
    memory.recall(useful.statement_id, utility=0.4)
    return {'proposals': 2}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        graph = Path(tmp) / 'stable.db'
        graph.write_bytes(b'stable-graph')
        result = ShadowCycle(graph).run_with_memory(candidate, evaporation_threshold=0.18)
        assert result.stable_unchanged
        assert result.status == 'completed'
        assert result.candidate_output['memory_evaporated_count'] == 1
        assert result.candidate_output['memory_survivor_count'] == 1
        print(result.candidate_output)


if __name__ == '__main__':
    main()
