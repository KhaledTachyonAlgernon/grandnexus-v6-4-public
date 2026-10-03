"""Optional LLM proposer adapter; never a decider."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.multiagent.experimental_group import AgentProposal, ExperimentalAgent


@dataclass
class LLMCallBudget:
    max_calls: int = 3
    calls: int = 0

    def consume(self) -> None:
        if self.calls >= self.max_calls:
            raise RuntimeError('LLM proposer call budget exhausted')
        self.calls += 1


class StructuredLLMProposer:
    """Lazy OpenAI-compatible proposer using gpt-5-mini by default."""

    def __init__(self, model: str = 'gpt-5-mini', budget: LLMCallBudget | None = None, client: Any | None = None):
        self.model = model
        self.budget = budget or LLMCallBudget()
        self._client = client
        self.last_usage = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def propose(self, request: CognitiveRequest) -> AgentProposal:
        self.budget.consume()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {'role': 'system', 'content': 'You are a cautious English proposal agent. Return only one concise candidate claim and up to three short evidence strings. Classify action_intent as none, describe, prepare, or execute. Use execute only when the user explicitly asks to perform an external action. Description of inability, failure, conflict, or negation is not execute. Never claim validation.'},
                {'role': 'user', 'content': request.objective},
            ],
            max_completion_tokens=300,
            response_format={'type': 'json_schema', 'json_schema': {'name': 'candidate_proposal', 'strict': True, 'schema': {'type': 'object', 'properties': {'claim': {'type': 'string'}, 'evidence': {'type': 'array', 'items': {'type': 'string'}}, 'confidence': {'type': 'number'}, 'action_intent': {'type': 'string', 'enum': ['none', 'describe', 'prepare', 'execute']}}, 'required': ['claim', 'evidence', 'confidence', 'action_intent'], 'additionalProperties': False}}},
        )
        self.last_usage = getattr(response, 'usage', None)
        raw = response.choices[0].message.content
        data = json.loads(raw)
        confidence = min(1.0, max(0.0, float(data['confidence'])))
        evidence = tuple(str(item)[:240] for item in data['evidence'][:3])
        action_intent = str(data['action_intent'])
        return AgentProposal('llm-proposer', str(data['claim'])[:500], confidence, evidence, action_intent == 'execute', 'claim-specific', action_intent)

    def as_agent(self) -> ExperimentalAgent:
        return ExperimentalAgent('llm-proposer', 'proposal', self.propose)
