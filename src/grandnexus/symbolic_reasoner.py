"""Small auditable forward-chaining reasoner for the level-14 MVP."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Fact:
    subject: str
    predicate: str
    value: bool = True

    @classmethod
    def parse(cls, text: str) -> 'Fact':
        raw = text.strip().rstrip('.')
        negative = raw.lower().startswith('not ')
        if negative:
            raw = raw[4:].strip()
        parts = raw.split()
        if len(parts) < 2:
            raise ValueError(f'invalid fact: {text}')
        return cls(parts[0], ' '.join(parts[1:]), not negative)

    def key(self) -> tuple[str, str]:
        return (self.subject.lower(), self.predicate.lower())


@dataclass(frozen=True)
class Rule:
    antecedent: str
    consequent: str
    rule_id: str = 'rule-1'


@dataclass(frozen=True)
class ProofStep:
    conclusion: Fact
    premises: tuple[Fact, ...] = ()
    rule_id: str | None = None


@dataclass
class SymbolicOutcome:
    query: Fact
    status: str
    confidence: float
    proof: list[ProofStep] = field(default_factory=list)
    contradictions: list[Fact] = field(default_factory=list)


class SymbolicReasoner:
    def __init__(self, facts: Iterable[Fact] = (), rules: Iterable[Rule] = ()):
        self.facts = list(facts)
        self.rules = list(rules)

    def prove(self, query: Fact) -> SymbolicOutcome:
        known = {(fact.key(), fact.value): fact for fact in self.facts}
        proof: list[ProofStep] = []
        changed = True
        while changed:
            changed = False
            for rule in self.rules:
                for fact in list(known.values()):
                    if fact.predicate.lower() == rule.antecedent.lower():
                        conclusion = Fact(fact.subject, rule.consequent, fact.value)
                        marker = (conclusion.key(), conclusion.value)
                        if marker not in known:
                            known[marker] = conclusion
                            proof.append(ProofStep(conclusion, (fact,), rule.rule_id))
                            changed = True
        positive = known.get((query.key(), True))
        negative = known.get((query.key(), False))
        contradictions = [fact for fact in (positive, negative) if fact is not None]
        if positive is not None and negative is not None:
            return SymbolicOutcome(query, 'contradiction', 0.0, proof, contradictions)
        if positive is not None and query.value:
            return SymbolicOutcome(query, 'proved', 1.0, proof, [])
        if negative is not None and not query.value:
            return SymbolicOutcome(query, 'proved', 1.0, proof, [])
        return SymbolicOutcome(query, 'unproved', 0.0, proof, [])
