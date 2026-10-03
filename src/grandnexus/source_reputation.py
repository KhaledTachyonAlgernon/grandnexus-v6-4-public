"""Source reputation is advisory evidence, never a truth oracle."""
from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable


@dataclass(frozen=True)
class SourceProfile:
    source_id: str
    family: str
    prior_confidence: float = 0.5
    confirmed: int = 0
    contradicted: int = 0
    unresolved: int = 0

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.family.strip():
            raise ValueError('source_id and family must be non-empty')
        if not 0.0 <= self.prior_confidence <= 1.0:
            raise ValueError('prior_confidence must be between 0 and 1')

    @property
    def empirical_reliability(self) -> float:
        total = self.confirmed + self.contradicted
        if total == 0:
            return self.prior_confidence
        # Shrink observations toward the prior to avoid reputation spikes.
        observed = (self.confirmed + 1.0) / (total + 2.0)
        weight = min(0.8, total / 10.0)
        return (1.0 - weight) * self.prior_confidence + weight * observed

    @property
    def reputation(self) -> float:
        uncertainty_penalty = min(0.2, self.unresolved * 0.01)
        return max(0.0, min(1.0, self.empirical_reliability - uncertainty_penalty))


@dataclass(frozen=True)
class EvidenceAssessment:
    weighted_support: float
    independent_families: int
    minimum_reputation: float
    quality: float
    promotable: bool
    reason: str


def assess_evidence(profiles: Iterable[SourceProfile], evidence_quality: float = 1.0, minimum_families: int = 2, minimum_weighted_support: float = 1.0, minimum_reputation: float = 0.55) -> EvidenceAssessment:
    profiles = tuple(profiles)
    if not 0.0 <= evidence_quality <= 1.0:
        raise ValueError('evidence_quality must be between 0 and 1')
    if minimum_families < 1:
        raise ValueError('minimum_families must be positive')
    if not profiles:
        return EvidenceAssessment(0.0, 0, 0.0, 0.0, False, 'no evidence')
    families = {profile.family for profile in profiles}
    reputations = [profile.reputation for profile in profiles]
    # Diminishing returns: five copies of one source do not equal five independent sources.
    weighted_support = evidence_quality * sum(profile.reputation for profile in profiles) / max(1.0, len(profiles) ** 0.5)
    quality = evidence_quality * (sum(reputations) / len(reputations))
    promotable = len(families) >= minimum_families and weighted_support >= minimum_weighted_support and min(reputations) >= minimum_reputation
    reason = 'evidence meets promotion gate' if promotable else 'evidence remains insufficient or too concentrated'
    return EvidenceAssessment(weighted_support, len(families), min(reputations), quality, promotable, reason)
