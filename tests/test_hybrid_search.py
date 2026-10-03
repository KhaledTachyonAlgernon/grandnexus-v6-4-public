from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.hybrid_search import HybridSemanticSearch
from grandnexus.semantic_ranker import SemanticRanker

candidates = [
    ('memory', 'validated semantic memory stores knowledge with provenance'),
    ('robot', 'simulation executes safe abstract action requests with limits'),
    ('graph', 'semantic graph links concepts through versioned relations'),
]
search = HybridSemanticSearch(SemanticRanker(prefer_ml=True), semantic_threshold=0.45)
hits = search.search('validated memory', candidates)
assert hits and hits[0].memory_id == 'memory'
negative = search.search('quantum poetry about blue mountains', candidates)
assert negative == []
try:
    search.search('   ', candidates)
except ValueError:
    pass
else:
    raise AssertionError('empty query accepted')
print('hybrid_search=OK')
