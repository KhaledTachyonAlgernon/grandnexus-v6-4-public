from __future__ import annotations

import json
from openai import OpenAI

from grandnexus.llm_bridge import LLMBridge

client = OpenAI()
bridge = LLMBridge(client.chat.completions, model='gpt-5-mini')

# Adapt the SDK method to the bridge's small client protocol.
class Adapter:
    def create(self, **kwargs):
        return client.chat.completions.create(**kwargs)

bridge = LLMBridge(Adapter(), model='gpt-5-mini')
items = bridge.extract_candidates('The simulated agent is at home and needs a key to open the door.', 'real-llm-test')
print(json.dumps([item.__dict__ for item in items], ensure_ascii=False, indent=2))
assert items
assert all(item.status == 'hypothesis' for item in items)
