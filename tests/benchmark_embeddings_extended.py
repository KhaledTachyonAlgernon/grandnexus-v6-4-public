from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_ranker import LexicalSemanticBackend, SemanticRanker

CANDIDATES = [
    ('validated_memory', 'validated semantic memory stores knowledge with provenance'),
    ('observation', 'raw observation from a camera with uncertain confidence'),
    ('hypothesis', 'hypothesis awaiting independent validation'),
    ('provenance', 'source provenance and validation history are retained'),
    ('robot', 'simulation executes safe abstract action requests with limits'),
    ('metacognition', 'confidence calibration compares predictions with observed outcomes'),
    ('graph', 'semantic graph links concepts through versioned relations'),
    ('planning', 'symbolic planner checks preconditions before simulated actions'),
    ('audio', 'audio transcript includes language and timestamps'),
    ('unrelated', 'weather forecast and cooking recipe for a distant topic'),
]
CASES = [
    ('semantic memory that is confirmed', {'validated_memory'}),
    ('camera perception not yet certain', {'observation'}),
    ('knowledge waiting for review', {'hypothesis'}),
    ('where did this information come from', {'provenance'}),
    ('safe movement in a virtual environment', {'robot'}),
    ('self evaluation of confidence', {'metacognition'}),
    ('network of concepts and relations', {'graph'}),
    ('steps required before an action', {'planning'}),
    ('spoken recording with time information', {'audio'}),
    ('quantum poetry about blue mountains', set()),
]

class CachedRanker:
    def __init__(self, ranker):
        self.ranker = ranker
        self.cache = {}
        self.name = ranker.backend_name + '+cache'
    @property
    def backend_name(self):
        return self.name
    def rank(self, query, candidates, limit=10):
        key = (query, tuple(candidates), limit)
        if key not in self.cache:
            self.cache[key] = self.ranker.rank(query, candidates, limit)
        return self.cache[key]

def evaluate(ranker, repeats=1, min_score=0.0):
    total = 0
    correct = 0
    reciprocal = 0.0
    false_positive = 0
    start = time.perf_counter()
    details = []
    for _ in range(repeats):
        for query, expected in CASES:
            results = ranker.rank(query, CANDIDATES, len(CANDIDATES))
            results = [item for item in results if item.score >= min_score]
            ids = [item.memory_id for item in results]
            rank = next((i + 1 for i, item_id in enumerate(ids) if item_id in expected), None)
            top = ids[0] if ids else None
            if expected:
                correct += int(rank is not None)
                reciprocal += 1.0 / rank if rank else 0.0
            else:
                false_positive += int(top is not None)
            total += 1
            if repeats == 1:
                details.append({'query': query, 'expected': sorted(expected), 'rank': rank, 'top': top})
    elapsed = time.perf_counter() - start
    positives = len(CASES) - 1
    return {'backend': ranker.backend_name, 'min_score': min_score, 'precision_like': correct / (positives * repeats), 'mrr': reciprocal / (positives * repeats), 'negative_false_positive_rate': false_positive / repeats, 'elapsed_ms': elapsed * 1000, 'details': details}

with tempfile.TemporaryDirectory():
    lexical = evaluate(SemanticRanker(backend=LexicalSemanticBackend()))
    output = {'lexical': lexical, 'model_available': importlib.util.find_spec('sentence_transformers') is not None}
    if output['model_available']:
        base = SemanticRanker(prefer_ml=True)
        output['embeddings_cold'] = evaluate(base)
        output['embeddings_threshold_0_45'] = evaluate(base, min_score=0.45)
        output['embeddings_threshold_0_55'] = evaluate(base, min_score=0.55)
        output['embeddings_repeated'] = evaluate(base, repeats=20)
        output['embeddings_cached'] = evaluate(CachedRanker(base), repeats=20)
    print(json.dumps(output, ensure_ascii=False, indent=2))
