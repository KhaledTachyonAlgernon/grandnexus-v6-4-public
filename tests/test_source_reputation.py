from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_knowledge import EpistemicStatus, SemanticKnowledgeBase
from grandnexus.source_reputation import SourceProfile, assess_evidence


def main():
    repeated = [SourceProfile('llm-a', 'llm', 0.55) for _ in range(3)]
    assert not assess_evidence(repeated).promotable
    independent = [SourceProfile('symbolic', 'symbolic', 0.8, confirmed=8), SourceProfile('human', 'human', 0.8, confirmed=8)]
    assessment = assess_evidence(independent, evidence_quality=0.95)
    assert assessment.promotable

    with tempfile.TemporaryDirectory() as tmp:
        kb = SemanticKnowledgeBase(Path(tmp) / 'memory.db', validation_threshold=1)
        statement = kb.hypothesize('agent', 'uses', 'semantic memory', 'llm-shadow', 0.7)
        kb.add_independent_support(statement.statement_id, 'symbolic')
        kb.add_independent_support(statement.statement_id, 'human')
        promoted = kb.promote(statement.statement_id, 'supervisor', evidence_profiles=independent, evidence_quality=0.95)
        assert promoted.status == EpistemicStatus.VALIDATED
    print({'repeated_source_rejected': True, 'independent_families_accepted': True, 'promoted': promoted.status.value})


if __name__ == '__main__':
    main()
