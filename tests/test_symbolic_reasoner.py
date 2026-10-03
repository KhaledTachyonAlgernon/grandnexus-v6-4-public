from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.symbolic_reasoner import Fact, Rule, SymbolicReasoner

reasoner = SymbolicReasoner(
    facts=[Fact('A', 'animal'), Fact('B', 'animal'), Fact('A', 'calm'), Fact('A', 'calm', False)],
    rules=[Rule('animal', 'breathes', 'animal-breathes')],
)
proved = reasoner.prove(Fact('A', 'breathes'))
unproved = reasoner.prove(Fact('C', 'breathes'))
contradiction = reasoner.prove(Fact('A', 'calm'))
assert proved.status == 'proved' and proved.confidence == 1.0
assert any(step.rule_id == 'animal-breathes' for step in proved.proof)
assert unproved.status == 'unproved' and not any(step.conclusion.subject == 'C' and step.conclusion.predicate == 'breathes' for step in unproved.proof)
assert contradiction.status == 'contradiction' and len(contradiction.contradictions) == 2
print('symbolic_reasoner=OK')
