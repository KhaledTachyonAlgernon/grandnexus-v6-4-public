from pathlib import Path
from types import SimpleNamespace
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.llm_bridge import LLMBridge

class FakeClient:
    def create(self, **kwargs):
        payload = json.dumps({'items': [{'subject': 'agent', 'predicate': 'needs', 'object': 'key', 'confidence': 0.74}]})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=payload))])

candidate = LLMBridge(FakeClient()).extract_candidates('The agent needs a key.', 'test')
assert len(candidate) == 1 and candidate[0].status == 'hypothesis'
assert candidate[0].confidence == 0.74
fallback = LLMBridge().extract_candidates('A perception.', 'sensor')
assert fallback[0].status == 'hypothesis' and fallback[0].confidence == 0.2
try:
    LLMBridge(FakeClient()).extract_candidates('   ')
except ValueError:
    pass
else:
    raise AssertionError('empty input accepted')
print('llm_bridge=OK')
