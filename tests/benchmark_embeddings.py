from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.graph_search import GraphSemanticSearch
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.semantic_ranker import LexicalSemanticBackend, SemanticRanker

CASES = [
    {'query': 'validated memory', 'expected': {'memory'}},
    {'query': 'knowledge provenance', 'expected': {'provenance'}},
    {'query': 'safe simulated action', 'expected': {'robot'}},
    {'query': 'confidence calibration', 'expected': {'metacognition'}},
    {'query': 'semantic graph relation', 'expected': {'graph'}},
]
CANDIDATES = [
    ('memory', 'validated semantic memory stores knowledge with provenance'),
    ('provenance', 'observations retain source confidence and validation history'),
    ('robot', 'simulation executes safe abstract action requests with limits'),
    ('metacognition', 'confidence calibration compares predictions with observed outcomes'),
    ('graph', 'semantic graph links concepts through versioned relations'),
]

def evaluate(ranker, cases):
    hits = 0
    reciprocal = 0.0
    started = time.perf_counter()
    details = []
    for case in cases:
        results = ranker.rank(case['query'], CANDIDATES, limit=len(CANDIDATES))
        ids = [item.memory_id for item in results]
        expected = case['expected']
        rank = next((index + 1 for index, item_id in enumerate(ids) if item_id in expected), None)
        if rank is not None:
            hits += 1
            reciprocal += 1.0 / rank
        details.append({'query': case['query'], 'rank': rank, 'top': ids[0] if ids else None})
    elapsed = time.perf_counter() - started
    return {'backend': ranker.backend_name, 'recall_at_5': hits / len(cases), 'mrr': reciprocal / len(cases), 'latency_ms_total': elapsed * 1000, 'details': details}

with tempfile.TemporaryDirectory() as tmp:
    graph = SemanticGraph(Path(tmp) / 'graph.db')
    nodes = {label: graph.add_node(label, kind='concept') for label in ['memory', 'provenance', 'robot', 'metacognition', 'graph']}
    for label, node in nodes.items():
        graph.relate(node, 'describes', node, GraphStatus.VALIDATED, 0.9, ('benchmark:current-graph',), 'v1')
    graph_search = GraphSemanticSearch(graph)
    graph_hits = graph_search.search('memory', validated_only=True)
    assert graph_hits and graph_hits[0].status == GraphStatus.VALIDATED

lexical = evaluate(SemanticRanker(backend=LexicalSemanticBackend()), CASES)
ml_available = importlib.util.find_spec('sentence_transformers') is not None
semantic = {'backend': 'not-run', 'available': ml_available}
if ml_available:
    semantic = evaluate(SemanticRanker(prefer_ml=True), CASES)
print(json.dumps({'lexical': lexical, 'semantic': semantic}, ensure_ascii=False, indent=2))
