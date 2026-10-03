from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.graph_anchor import parse_structured_claim


def main():
    claim = parse_structured_claim('Every agent must use its semantic memory')
    assert claim and claim.subject == 'agent' and claim.predicate == 'use'
    assert claim.object == 'semantic memory'
    assert claim.quantifier == 'universal' and claim.modality == 'necessary'

    negated = parse_structured_claim('The robot does not open the door')
    assert negated and negated.polarity == 'negative'

    scoped = parse_structured_claim('The agent uses semantic memory but the evidence concerns the audio sensor')
    assert scoped and scoped.scope_complete is False
    print({'triplet': (claim.subject, claim.predicate, claim.object), 'negative': negated.polarity, 'scope_complete': scoped.scope_complete})


if __name__ == '__main__':
    main()
