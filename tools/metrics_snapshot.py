from __future__ import annotations
import json
from pathlib import Path

source = Path(__file__).resolve().parents[1] / 'embedding_benchmark_extended2.json'
data = json.loads(source.read_text())
rows = []
for name, result in data.items():
    if not isinstance(result, dict) or 'precision_like' not in result:
        continue
    rows.append({
        'profile': name,
        'backend': result.get('backend'),
        'recall_like': result.get('precision_like'),
        'mrr': result.get('mrr'),
        'negative_false_positive_rate': result.get('negative_false_positive_rate'),
        'elapsed_ms': result.get('elapsed_ms'),
    })
output = Path(__file__).resolve().parents[1] / 'metrics_snapshot.json'
output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(rows, ensure_ascii=False, indent=2))
