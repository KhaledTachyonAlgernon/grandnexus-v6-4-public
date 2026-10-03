"""Load approved knowledge versions into the auditable symbolic reasoner."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .learning_experiment import SlowLearningStore
from .symbolic_reasoner import Fact, Rule, SymbolicOutcome, SymbolicReasoner


@dataclass(frozen=True)
class ReuseResult:
    outcome: SymbolicOutcome
    knowledge_version: str
    rules_loaded: int


class ReusableKnowledge:
    def __init__(self, store: SlowLearningStore):
        self.store = store

    def rules(self) -> list[Rule]:
        version = self.store.current()
        return [
            Rule(antecedent=str(antecedent), consequent=str(consequent), rule_id=f"{version.version_id}:{antecedent}->{consequent}")
            for antecedent, consequent in version.knowledge.items()
        ]

    def reason(self, facts: list[Fact], query: Fact) -> ReuseResult:
        version = self.store.current()
        rules = self.rules()
        outcome = SymbolicReasoner(facts=facts, rules=rules).prove(query)
        return ReuseResult(outcome=outcome, knowledge_version=version.version_id, rules_loaded=len(rules))

    def export(self) -> dict[str, Any]:
        version = self.store.current()
        return {"version": version.version_id, "knowledge": version.knowledge, "rules": [rule.__dict__ for rule in self.rules()]}
