from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.semantic_knowledge import EpistemicStatus, SemanticKnowledgeBase


def main():
    with tempfile.TemporaryDirectory() as tmp:
        kb = SemanticKnowledgeBase(Path(tmp) / 'memory.db')
        recent = kb.hypothesize('agent', 'uses', 'semantic memory', 'llm-shadow', 0.7)
        old = kb.hypothesize('mars', 'has', 'weather tomorrow', 'llm-shadow', 0.4, {'_memory': {'last_recalled_at': 0}})
        conflicted = kb.hypothesize('system', 'state', 'active and stopped', 'llm-shadow', 0.4, {'_memory': {'last_recalled_at': 0}})
        conflicted = kb.contradict(conflicted.statement_id, 'stable-checker')
        validated = kb.hypothesize('grandnexus', 'has', 'validated ontology', 'human-review', 0.8, {'_memory': {'last_recalled_at': 0}})
        validated = kb.validate(validated.statement_id, 'validator-a')
        validated = kb.validate(validated.statement_id, 'validator-b')
        removed = kb.evaporate(threshold=0.18, now=86400 * 365)
        assert recent.statement_id not in removed
        assert old.statement_id in removed
        assert conflicted.statement_id in removed
        assert validated.statement_id not in removed
        assert kb.get(validated.statement_id).status == EpistemicStatus.VALIDATED
        print({'surviving_recent': recent.statement_id not in removed, 'evaporated_old': old.statement_id in removed, 'evaporated_conflicted': conflicted.statement_id in removed, 'validated_protected': validated.statement_id not in removed, 'removed_count': len(removed)})


if __name__ == '__main__':
    main()
