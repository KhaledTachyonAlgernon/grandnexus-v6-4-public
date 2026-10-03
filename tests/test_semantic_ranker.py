from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_ranker import SemanticRanker

candidates = [
    ('m1', 'Le chat dort sur le tapis'),
    ('m2', 'Le système conserve une connaissance validée'),
    ('m3', 'La plante reçoit de la lumière'),
]
ranker = SemanticRanker(prefer_ml=True)
results = ranker.rank('connaissance validée', candidates)
assert ranker.backend_name in {'lexical-fallback', 'sentence-transformers'}
assert results and results[0].memory_id == 'm2'
assert results[0].score > 0
try:
    ranker.rank('   ', candidates)
except ValueError:
    pass
else:
    raise AssertionError('empty query must be rejected')
print('semantic_ranker=OK')
