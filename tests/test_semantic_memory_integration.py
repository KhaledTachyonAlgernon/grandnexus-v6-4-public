from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.memory_index import ExplainableMemoryIndex
from grandnexus.semantic_ranker import SemanticRanker

with tempfile.TemporaryDirectory() as tmp:
    index = ExplainableMemoryIndex(Path(tmp) / 'memory.db', ranker=SemanticRanker())
    index.add('m1', 'Le chat dort sur le tapis', kind='episode')
    index.add('m2', 'Une règle validée concerne la mémoire sémantique', kind='rule')
    hits = index.search('règle mémoire sémantique')
    assert hits[0].memory_id == 'm2'
    assert hits[0].kind == 'rule'
    assert hits[0].score > 0
print('semantic_memory_integration=OK')
