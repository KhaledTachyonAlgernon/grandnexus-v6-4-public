from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_graph import SemanticGraph
from grandnexus.shadow_cycle import ShadowCycle

with tempfile.TemporaryDirectory() as tmp:
    stable_db = Path(tmp) / 'stable.db'
    graph = SemanticGraph(stable_db)
    graph.add_node('stable-root', node_id='root')
    stable_before = stable_db.read_bytes()
    cycle = ShadowCycle(stable_db)

    def candidate(candidate_db):
        shadow = SemanticGraph(candidate_db)
        shadow.add_node('candidate-knowledge', node_id='candidate')
        return {'candidate_nodes': len(shadow.neighbors('root')), 'proposal': 'hypothesis-only'}

    result = cycle.run(candidate)
    assert result.status == 'completed'
    assert result.stable_unchanged
    assert stable_db.read_bytes() == stable_before
    assert result.candidate_hash != result.stable_hash_before

    failed = cycle.run(lambda _path: 1 / 0)
    assert failed.status == 'failed' and failed.stable_unchanged
    assert stable_db.read_bytes() == stable_before
print('shadow_cycle=OK')
