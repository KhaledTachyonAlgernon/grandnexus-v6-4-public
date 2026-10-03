from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_knowledge import EpistemicStatus, SemanticKnowledgeBase


def main():
    with tempfile.TemporaryDirectory() as tmp:
        kb = SemanticKnowledgeBase(Path(tmp) / 'memory.db', validation_threshold=1)
        weak = kb.hypothesize('agent', 'uses', 'unknown tool', 'llm-shadow', 0.6)
        try:
            kb.promote(weak.statement_id, 'supervisor')
        except ValueError as exc:
            assert 'insufficient' in str(exc)
        else:
            raise AssertionError('weak hypothesis was promoted')

        contradicted = kb.hypothesize('system', 'state', 'active', 'llm-shadow', 0.8)
        kb.add_independent_support(contradicted.statement_id, 'sensor-a')
        kb.add_independent_support(contradicted.statement_id, 'sensor-b')
        kb.contradict(contradicted.statement_id, 'stable-checker')
        try:
            kb.promote(contradicted.statement_id, 'supervisor')
        except ValueError as exc:
            assert 'contradicted' in str(exc)
        else:
            raise AssertionError('contradicted hypothesis was promoted')

        strong = kb.hypothesize('agent', 'uses', 'semantic memory', 'llm-shadow', 0.7)
        kb.add_independent_support(strong.statement_id, 'symbolic-checker')
        kb.add_independent_support(strong.statement_id, 'human-review')
        promoted = kb.promote(strong.statement_id, 'supervisor')
        assert promoted.status == EpistemicStatus.VALIDATED
        rolled_back = kb.rollback_promotion(strong.statement_id, 'supervisor')
        assert rolled_back.status == EpistemicStatus.HYPOTHESIS
        print({'weak_rejected': True, 'contradicted_rejected': True, 'promoted_then_rolled_back': rolled_back.status.value})


if __name__ == '__main__':
    main()
