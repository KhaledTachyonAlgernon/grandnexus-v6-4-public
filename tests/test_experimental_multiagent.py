from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_contracts import CognitiveRequest
from grandnexus.multiagent.experimental_group import ExperimentalMultiAgentGroup
from grandnexus.source_reputation import SourceProfile


def main():
    profiles = (
        SourceProfile('symbolic', 'symbolic', 0.8, confirmed=8),
        SourceProfile('human', 'human', 0.8, confirmed=8),
    )
    group = ExperimentalMultiAgentGroup(source_profiles=profiles)
    supported = group.run(CognitiveRequest('Analyser la règle validée du graphe'))
    assert supported.consensus == 'candidate-supported'
    assert supported.action_allowed is False
    assert supported.simulation_only is True

    external = group.run(CognitiveRequest('Commander un actionneur réel immédiatement'))
    assert external.consensus == 'candidate-rejected'
    assert external.action_allowed is False
    assert external.verification.payload['verified'] is False

    no_sources = ExperimentalMultiAgentGroup().run(CognitiveRequest('Analyser une hypothèse sans source'))
    assert no_sources.consensus == 'candidate-unverified'
    print({'supported': supported.consensus, 'external_action': external.consensus, 'no_sources': no_sources.consensus})


if __name__ == '__main__':
    main()
