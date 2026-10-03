import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from grandnexus.autonomy_level1 import AutonomyLevelOne
from grandnexus.drive_module import DriveModule
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction
from grandnexus.verification_experiment_proposer import VerificationCapability

OUTPUT = Path(__file__).resolve().parents[1] / 'verification_experiment_multienv_observation.json'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_actions() -> list[SimAction]:
    return [
        SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
        SimAction('open_door', frozenset({'has:key'}), frozenset({'door:open'}), frozenset({'door:closed'})),
        SimAction('enter_room', frozenset({'at:home', 'door:open'}), frozenset({'at:room'}), frozenset({'at:home'})),
        SimAction('return_home', frozenset({'at:room'}), frozenset({'at:home'}), frozenset({'at:room'})),
        SimAction('close_door', frozenset({'at:home', 'door:open'}), frozenset({'door:closed'}), frozenset({'door:open'})),
        SimAction('survey_beacon', frozenset({'at:room', 'beacon:visible'}), frozenset({'beacon:surveyed'})),
    ]


def verification_action() -> SimAction:
    return SimAction(
        'verify_beacon_visibility',
        frozenset({'at:room'}),
        frozenset({'observation:beacon:visible'}),
    )


def capability() -> VerificationCapability:
    return VerificationCapability(
        'beacon-visibility-observation',
        'beacon:visible',
        'verify_beacon_visibility',
        'observation:beacon:visible',
        'simulation-only observation of beacon visibility',
    )


def run_environment(name: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path = root / 'graph.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('verification-multienv-seed',), 'v1')
        graph_before = digest(graph_path)
        world_path = root / 'world.db'
        loop = IntegratedCognitiveLoop(graph, base_actions(), root / 'learning.db', root / 'trace.db', world_state_db=world_path)
        autonomy = AutonomyLevelOne(
            loop,
            DriveModule(root / 'drives.db'),
            'agent',
            verification_actions=(verification_action(),),
            verification_capabilities=(capability(),),
        )
        rows = []
        for cycle in range(1, 49):
            if name == 'new_opportunity' and cycle == 25:
                loop.world_state.apply_transition('agent', {'beacon:visible'}, (), 'environment', 'inject-beacon-opportunity')
            if name == 'safety_conflict' and cycle == 25:
                loop.world_state.apply_transition('agent', {'door:open', 'door:closed'}, (), 'environment', 'inject-conflict')
            if name == 'safety_conflict' and cycle == 29:
                loop.world_state.apply_transition('agent', (), {'door:open', 'door:closed'}, 'environment', 'resolve-conflict')
            rows.append(autonomy.step(cycle).to_dict())
        final = loop.world_state.snapshot('agent')
        review_rows = [row for row in rows if row['status'] == 'trajectory_review']
        gap_rows = [row for row in review_rows if row['gap_status'] == 'hypotheses_available']
        verification_rows = [row for row in review_rows if row['verification_status'] == 'candidates_evaluated']
        safety_rows = [row for row in rows if row['status'] == 'verification_first']
        return {
            'name': name,
            'cycles': rows,
            'summary': {
                'accepted': sum(row['accepted'] for row in rows),
                'trajectory_reviews': len(review_rows),
                'first_review': review_rows[0]['cycle'] if review_rows else None,
                'gap_reviews': len(gap_rows),
                'verification_reviews': len(verification_rows),
                'verification_candidates': sum(len(row['verification_experiments']) for row in verification_rows),
                'all_candidates_shadow_simulated': all('shadow simulation=True' in item for row in verification_rows for item in row['verification_experiments']),
                'review_state_unchanged': all(row['state_revision_before'] == row['state_revision_after'] for row in review_rows),
                'safety_pauses': len(safety_rows),
                'beacon_surveyed': any(row['objective'] == 'beacon:surveyed' and row['success'] for row in rows),
                'resumed_after_conflict': any(row['cycle'] > 29 and row['accepted'] for row in rows),
                'pending_knowledge': loop.learning.current().knowledge == {},
                'graph_unchanged': graph_before == digest(graph_path),
                'no_observation_in_stable_state': not any(fact.startswith('observation:') for fact in final.facts),
                'world_facts': sorted(final.facts),
                'world_conflicts': list(final.conflicts),
                'statuses': dict(Counter(row['status'] for row in rows)),
            },
        }


def main():
    result = {name: run_environment(name) for name in ('repetition_only', 'new_opportunity', 'safety_conflict')}
    repetition = result['repetition_only']['summary']
    opportunity = result['new_opportunity']['summary']
    safety = result['safety_conflict']['summary']
    assert repetition['verification_reviews'] >= 1
    assert repetition['verification_candidates'] >= 1
    assert repetition['all_candidates_shadow_simulated'] is True
    assert repetition['review_state_unchanged'] is True
    assert opportunity['beacon_surveyed'] is True
    assert safety['safety_pauses'] >= 4
    assert safety['resumed_after_conflict'] is True
    assert all(row['summary']['pending_knowledge'] for row in result.values())
    assert all(row['summary']['graph_unchanged'] for row in result.values())
    assert all(row['summary']['no_observation_in_stable_state'] for row in result.values())
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({name: result[name]['summary'] for name in result}, indent=2))


if __name__ == '__main__':
    main()
