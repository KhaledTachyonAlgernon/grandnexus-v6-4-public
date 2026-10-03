"""Optional LLM bridge: proposal only, never truth or action."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol


@dataclass(frozen=True)
class ExtractionCandidate:
    subject: str
    predicate: str
    object: str
    confidence: float
    source: str
    status: str = 'hypothesis'


class ChatClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class LLMBridge:
    def __init__(self, client: ChatClient | None = None, model: str = 'gpt-5-mini'):
        self.client = client
        self.model = model

    @property
    def available(self) -> bool:
        return self.client is not None

    def extract_candidates(self, text: str, source: str = 'llm-input') -> list[ExtractionCandidate]:
        if not text.strip():
            raise ValueError('text must be non-empty')
        if self.client is None:
            return self._fallback(text, source)
        response = self._create_completion(
            model=self.model,
            messages=[
                {'role': 'system', 'content': 'Extract possible knowledge claims. Return hypotheses only; never claim validation.'},
                {'role': 'user', 'content': text},
            ],
            response_format={
                'type': 'json_schema',
                'json_schema': {
                    'name': 'knowledge_candidates',
                    'strict': True,
                    'schema': {
                        'type': 'object',
                        'properties': {'items': {'type': 'array', 'items': {'type': 'object', 'properties': {
                            'subject': {'type': 'string'}, 'predicate': {'type': 'string'}, 'object': {'type': 'string'}, 'confidence': {'type': 'number'},
                        }, 'required': ['subject', 'predicate', 'object', 'confidence'], 'additionalProperties': False}}},
                        'required': ['items'], 'additionalProperties': False,
                    },
                },
            },
            max_completion_tokens=500,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return [self._candidate(item, source) for item in data['items']]

    def _create_completion(self, **kwargs: Any) -> Any:
        if hasattr(self.client, 'chat') and hasattr(self.client.chat, 'completions'):
            return self.client.chat.completions.create(**kwargs)
        return self.client.create(**kwargs)

    def _candidate(self, item: dict[str, Any], source: str) -> ExtractionCandidate:
        fields = [item.get('subject'), item.get('predicate'), item.get('object')]
        if not all(isinstance(value, str) and value.strip() for value in fields):
            raise ValueError('invalid candidate fields')
        confidence = float(item.get('confidence', 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError('candidate confidence must be between 0 and 1')
        return ExtractionCandidate(*(value.strip() for value in fields), confidence, source)

    def _fallback(self, text: str, source: str) -> list[ExtractionCandidate]:
        return [ExtractionCandidate('input', 'mentions', text.strip(), 0.2, source)]
