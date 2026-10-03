"""Explainable proposal-to-graph anchoring for the shadow branch."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import sqlite3
from pathlib import Path

from grandnexus.semantic_graph import GraphStatus, SemanticGraph


@dataclass(frozen=True)
class StructuredClaim:
    subject: str
    predicate: str
    object: str
    polarity: str = 'positive'
    scope_complete: bool = True
    quantifier: str = 'specific'
    modality: str = 'asserted'


@dataclass(frozen=True)
class GraphAnchorAssessment:
    matched_relation_ids: tuple[str, ...]
    matched_statuses: tuple[str, ...]
    matched_provenance: tuple[str, ...]
    lexical_alignment: float
    validated_anchor: bool
    contradiction: bool
    reason: str
    claim: StructuredClaim | None = None


TERM_ALIASES = {
    'utilise': 'use', 'utiliser': 'use', 'uses': 'use',
    'mémoire': 'memory', 'memoire': 'memory',
    'sémantique': 'semantic', 'semantique': 'semantic',
    'ouvre': 'open', 'opens': 'open',
    'voit': 'see', 'vois': 'see', 'sees': 'see',
    'porte': 'door', 'door': 'door',
    'actif': 'active', 'active': 'active', 'idle': 'stopped',
    'arrêté': 'stopped', 'arrete': 'stopped', 'stopped': 'stopped',
    'l’agent': 'agent', 'agent': 'agent',
}


def _terms(value: str) -> set[str]:
    terms = {term.lower() for term in re.findall(r'[\wÀ-ÿ]+', value) if len(term) > 3}
    return {TERM_ALIASES.get(term, term) for term in terms}


def parse_structured_claim(claim: str) -> StructuredClaim | None:
    lowered = claim.lower().replace('’', "'")
    polarity = 'negative' if any(marker in lowered for marker in (' does not ', ' do not ', ' not ', "n't ", ' failed to ', ' unable to ', ' cannot ', 'nouvre pas', "n'ouvre pas", 'n ouvre pas')) else 'positive'
    tokens = set(re.findall(r'[a-z]+', lowered))
    quantifier = 'universal' if {'every', 'each', 'all'} & tokens else ('existential' if {'some'} & tokens or 'at least one' in lowered else ('none' if {'no', 'none'} & tokens else 'specific'))
    modality = 'necessary' if {'must', 'necessarily'} & tokens else ('possible' if {'may', 'might', 'possibly'} & tokens else 'asserted')
    scope_complete = not any(marker in lowered for marker in (' but the evidence ', ' however the evidence ', ' although the evidence ', ' mais la preuve ', ' toutefois la preuve '))
    patterns = (
        (r'(?:the |le |l\'|l’)?agent .*?(?:uses|use|utilizes|utilise|makes use of|recours à|se sert de) (?:its |sa |la |the )?(semantic memory|episodic memory|audio sensor|memory)', 'use'),
        (r'(?:the |le |l\'|l’)?agent .*?(?:stores|stores and retrieves|retrieves).*?(semantic memory|episodic memory|audio sensor|memory)', 'use'),
        (r'(?:the |le |l\'|l’)?robot .*?(?:does not open|do not open|failed to open|unable to open|cannot open|opens|ouvre|nouvre pas|n\'ouvre pas) (?:the |la |la )?(door|porte)', 'open'),
        (r'(?:the |le |l\'|l’)?system .*?(?:is|est) (active|idle|stopped|arrêté|arrete|en veille)', 'state'),
    )
    for pattern, predicate in patterns:
        match = re.search(pattern, lowered)
        if match:
            subject = 'robot' if 'robot' in match.group(0) else ('system' if any(word in match.group(0) for word in ('system', 'système')) else 'agent')
            return StructuredClaim(subject, predicate, match.group(1).lower(), polarity, scope_complete, quantifier, modality)
    return None


def assess_graph_anchor(graph: SemanticGraph, claim: str, evidence: tuple[str, ...] = ()) -> GraphAnchorAssessment:
    lowered = claim.lower()
    structured = parse_structured_claim(claim)
    if any(marker in lowered for marker in ('jamais observ', 'aucune preuve', 'sans source', 'inconnu')):
        return GraphAnchorAssessment((), (), (), 0.0, False, False, 'claim explicitly marks absent evidence', structured)
    if any(marker in lowered for marker in ('mismatch', 'evidence concerns', 'evidence pertains', 'modality conflict', 'source conflict')):
        return GraphAnchorAssessment((), (), (), 0.0, False, False, 'claim explicitly marks evidence conflict', structured)
    if structured and not structured.scope_complete:
        return GraphAnchorAssessment((), (), (), 0.0, False, False, 'claim has incomplete or conflicting evidence scope', structured)
    claim_terms = _terms(claim)
    matched = []
    with sqlite3.connect(graph.db_file) as conn:
        rows = conn.execute('SELECT r.relation_id, r.predicate, r.status, r.provenance, n1.label, n2.label FROM graph_relations r LEFT JOIN graph_nodes n1 ON n1.node_id = r.source_id LEFT JOIN graph_nodes n2 ON n2.node_id = r.target_id').fetchall()
    if structured:
        claim_subject = next(iter(_terms(structured.subject)), structured.subject.lower())
        claim_predicate = next(iter(_terms(structured.predicate)), structured.predicate.lower())
        claim_object = ' '.join(sorted(_terms(structured.object)))
        for relation_id, predicate, status, provenance, source, target in rows:
            relation_subject = next(iter(_terms(source or '')), '')
            relation_predicate = next(iter(_terms(predicate)), predicate.lower())
            relation_object = ' '.join(sorted(_terms(target or '')))
            exact = relation_subject == claim_subject and relation_predicate == claim_predicate and relation_object == claim_object
            polarity_match = structured.polarity == 'positive' or status == GraphStatus.REJECTED.value
            if exact and polarity_match:
                matched.append((relation_id, status, json.loads(provenance), 3))
    else:
        for relation_id, predicate, status, provenance, source, target in rows:
            relation_text = ' '.join(filter(None, (source, predicate, target)))
            overlap = claim_terms & _terms(relation_text)
            if overlap and len(overlap) / max(1, len(claim_terms)) >= 0.25:
                matched.append((relation_id, status, json.loads(provenance), len(overlap)))
    if not matched:
        return GraphAnchorAssessment((), (), (), 0.0, False, False, 'no graph relation anchored to claim', structured)
    best_overlap = max(item[3] for item in matched)
    best = [item for item in matched if item[3] == best_overlap]
    statuses = tuple(sorted({item[1] for item in best}))
    provenance = tuple(sorted({source for item in best for source in item[2]}))
    contradiction = GraphStatus.REJECTED.value in statuses
    validated = GraphStatus.VALIDATED.value in statuses and not contradiction
    alignment = best_overlap / max(1, len(claim_terms))
    reason = 'validated graph anchor' if validated else ('graph contradiction' if contradiction else 'non-validated graph anchor')
    return GraphAnchorAssessment(tuple(item[0] for item in best), statuses, provenance, round(alignment, 3), validated, contradiction, reason, structured)
