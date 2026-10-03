"""Local, simulation-only multi-agent experiment for GrandNexus."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from grandnexus.branch_contracts import AgentMessage, CognitiveRequest
from grandnexus.graph_anchor import GraphAnchorAssessment, assess_graph_anchor
from grandnexus.semantic_graph import SemanticGraph
from grandnexus.source_reputation import EvidenceAssessment, SourceProfile, assess_evidence


@dataclass(frozen=True)
class AgentProposal:
    agent_id: str
    claim: str
    confidence: float
    evidence: tuple[str, ...]
    action_requested: bool = False
    evidence_scope: str = 'claim-specific'
    action_intent: str = 'none'


@dataclass(frozen=True)
class GroupResult:
    request_id: str
    proposal: AgentProposal
    critiques: tuple[AgentMessage, ...]
    verification: AgentMessage
    consensus: str
    evidence_assessment: EvidenceAssessment
    graph_anchor: GraphAnchorAssessment | None = None
    action_allowed: bool = False
    simulation_only: bool = True
    degraded_mode: bool = False


class ExperimentalAgent:
    def __init__(self, agent_id: str, role: str, handler: Callable[[CognitiveRequest], AgentProposal]):
        self.agent_id = agent_id
        self.role = role
        self.handler = handler

    def propose(self, request: CognitiveRequest) -> AgentProposal:
        proposal = self.handler(request)
        if proposal.agent_id != self.agent_id:
            raise ValueError('agent handler returned an invalid agent_id')
        return proposal


def default_proposer(request: CognitiveRequest) -> AgentProposal:
    text = request.objective.strip()
    lowered = text.lower()
    has_source = not any(marker in lowered for marker in ('sans source', 'jamais observé', 'aucune preuve'))
    evidence = (text,) if has_source else ()
    return AgentProposal('proposer', text, 0.55, evidence, any(word in lowered for word in ('exécuter', 'commander', 'actionner', 'execute', 'command', 'activate')))


def default_critic(request: CognitiveRequest, proposal: AgentProposal) -> AgentMessage:
    warnings = []
    if proposal.action_requested or proposal.action_intent == 'execute':
        warnings.append('external-action-request')
    elif proposal.action_intent == 'prepare':
        warnings.append('action-preparation-only')
    if not proposal.evidence:
        warnings.append('missing-evidence')
    elif proposal.evidence_scope != 'claim-specific':
        warnings.append('evidence-scope-unclear')
    return AgentMessage('critic', 'coordinator', 'critique', {'warnings': warnings, 'supports': list(proposal.evidence), 'accepted_for_shadow': not warnings})


def default_verifier(request: CognitiveRequest, proposal: AgentProposal, critiques: tuple[AgentMessage, ...]) -> AgentMessage:
    warnings = [warning for critique in critiques for warning in critique.payload.get('warnings', [])]
    claim_terms = {term.lower() for term in request.objective.split() if len(term) > 3}
    evidence_terms = {term.lower() for item in proposal.evidence for term in item.split() if len(term) > 3}
    alignment = len(claim_terms & evidence_terms) / max(1, len(claim_terms))
    if proposal.evidence and alignment < 0.25:
        warnings.append('evidence-not-linked-to-claim')
    verified = not warnings and bool(proposal.evidence) and alignment >= 0.25
    return AgentMessage('verifier', 'coordinator', 'evidence', {'verified': verified, 'warnings': warnings, 'proof': list(proposal.evidence), 'claim_alignment': round(alignment, 3)})


class ExperimentalMultiAgentGroup:
    """A local group that cannot mutate knowledge or execute actions."""

    def __init__(self, proposer: ExperimentalAgent | None = None, source_profiles: tuple[SourceProfile, ...] = (), graph: SemanticGraph | None = None):
        self.proposer = proposer or ExperimentalAgent('proposer', 'proposal', default_proposer)
        self.source_profiles = source_profiles
        self.graph = graph

    def run(self, request: CognitiveRequest) -> GroupResult:
        degraded_mode = False
        try:
            proposal = self.proposer.propose(request)
        except Exception:
            proposal = default_proposer(request)
            degraded_mode = True
        critique = default_critic(request, proposal)
        critiques = (critique,)
        verification = default_verifier(request, proposal, critiques)
        assessment = assess_evidence(self.source_profiles, evidence_quality=0.8, minimum_weighted_support=0.8) if self.source_profiles else assess_evidence(())
        anchor = assess_graph_anchor(self.graph, proposal.claim, proposal.evidence) if self.graph else None
        graph_ok = anchor is None or anchor.validated_anchor
        graph_conflict = anchor is not None and anchor.contradiction
        if verification.payload['verified'] and assessment.promotable and graph_ok:
            consensus = 'candidate-supported'
        elif graph_conflict:
            consensus = 'candidate-rejected'
        elif 'external-action-request' in verification.payload['warnings']:
            consensus = 'candidate-rejected'
        else:
            consensus = 'candidate-unverified'
        return GroupResult(request.request_id, proposal, critiques, verification, consensus, assessment, anchor, action_allowed=False, simulation_only=True, degraded_mode=degraded_mode)
