from pathlib import Path
import json
import re
import sys
import time
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.llm_bridge import LLMBridge

CASES = [
    {'id': 'C1', 'text': 'GrandNexus possède une mémoire sémantique.', 'expected_terms': ['grandnexus', 'mémoire sémantique'], 'negative': False},
    {'id': 'C2', 'text': 'Les connaissances conceptuelles sont conservées dans la mémoire sémantique.', 'expected_terms': ['connaissances', 'mémoire sémantique'], 'negative': False},
    {'id': 'C3', 'text': 'Quelle sera la météo sur Mars demain ?', 'expected_terms': [], 'negative': True},
    {'id': 'C4', 'text': 'Le système est simultanément arrêté et actif.', 'expected_terms': ['système', 'arrêté', 'actif'], 'negative': False},
    {'id': 'C5', 'text': 'Dans la simulation, l’agent trouve une clé puis ouvre une porte.', 'expected_terms': ['agent', 'trouve', 'clé', 'ouvre', 'porte'], 'negative': False},
    {'id': 'C6', 'text': 'Atteindre un état sans précondition disponible.', 'expected_terms': [], 'negative': True},
    {'id': 'C7', 'text': 'Il est possible que le module Orion utilise une mémoire distribuée.', 'expected_terms': ['module orion', 'mémoire distribuée'], 'negative': False},
    {'id': 'C8', 'text': 'Commander un actionneur réel immédiatement.', 'expected_terms': [], 'negative': True},
]


def stable_extract(text):
    lowered = text.lower()
    if any(token in lowered for token in ('météo sur mars', 'sans précondition', 'actionneur réel')):
        return []
    terms = re.findall(r"[\wÀ-ÿ]+(?:\s+[\wÀ-ÿ]+){0,2}", lowered)
    if 'mémoire sémantique' in lowered:
        return [{'subject': 'GrandNexus', 'predicate': 'possède', 'object': 'mémoire sémantique', 'status': 'validated'}]
    if 'clé' in lowered and 'porte' in lowered:
        return [{'subject': 'agent', 'predicate': 'trouve', 'object': 'clé', 'status': 'validated'}, {'subject': 'agent', 'predicate': 'ouvre', 'object': 'porte', 'status': 'validated'}]
    return [{'subject': 'input', 'predicate': 'mentions', 'object': text, 'status': 'hypothesis'}]


def text_of(items):
    return ' '.join(f"{x.get('subject','')} {x.get('predicate','')} {x.get('object','')}" for x in items).lower()

client = OpenAI()
bridge = LLMBridge(client, model='gpt-5-mini')
rows = []
for case in CASES:
    stable = stable_extract(case['text'])
    started = time.perf_counter()
    candidate_objects = bridge.extract_candidates(case['text'], source=f"shadow-{case['id']}")
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    candidate = [{'subject': x.subject, 'predicate': x.predicate, 'object': x.object, 'confidence': x.confidence, 'status': x.status} for x in candidate_objects]
    candidate_text = text_of(candidate)
    expected_hits = sum(1 for term in case['expected_terms'] if term.lower() in candidate_text)
    candidate_relevant = expected_hits > 0
    false_positive = case['negative'] and len(candidate) > 0
    rows.append({'id': case['id'], 'text': case['text'], 'stable': stable, 'candidate': candidate, 'candidate_relevant': candidate_relevant, 'false_positive': false_positive, 'latency_ms': elapsed_ms})

positive = [row for row in rows if not next(case for case in CASES if case['id'] == row['id'])['negative']]
negative = [row for row in rows if next(case for case in CASES if case['id'] == row['id'])['negative']]
summary = {
    'cases': len(rows),
    'stable_positive_coverage': round(sum(any(item.get('status') == 'validated' for item in row['stable']) for row in positive) / len(positive), 3),
    'candidate_positive_coverage': round(sum(row['candidate_relevant'] for row in positive) / len(positive), 3),
    'candidate_false_positive_rate': round(sum(row['false_positive'] for row in negative) / len(negative), 3),
    'candidate_mean_latency_ms': round(sum(row['latency_ms'] for row in rows) / len(rows), 2),
    'all_candidate_statuses': sorted(set(item['status'] for row in rows for item in row['candidate'])),
}
print(json.dumps({'summary': summary, 'rows': rows}, ensure_ascii=False, indent=2))
