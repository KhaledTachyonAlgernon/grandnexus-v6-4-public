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

OUTPUT = Path(__file__).resolve().parents[1] / 'trajectory_multienv_observation.json'


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


def run_environment(name: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path = root / 'graph.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('multienv-seed',), 'v1')
        graph_before = digest(graph_path)
        loop = IntegratedCognitiveLoop(graph, base_actions(), root / 'learning.db', root / 'trace.db', world_state_db=root / 'world.db')
        autonomy = AutonomyLevelOne(loop, DriveModule(root / 'drives.db'), 'agent')
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
        safety_rows = [row for row in rows if row['status'] == 'verification_first']
        return {
            'name': name,
            'cycles': rows,
            'summary': {
                'accepted': sum(row['accepted'] for row in rows),
                'trajectory_reviews': len(review_rows),
                'first_review': review_rows[0]['cycle'] if review_rows else None,
                'review_proposals': sum(bool(row['learning_proposal_id']) for row in review_rows),
                'gap_reviews': len(gap_rows),
                'gap_hypotheses': sum(len(row['gap_hypotheses']) for row in gap_rows),
                'safety_pauses': len(safety_rows),
                'beacon_surveyed': any(row['objective'] == 'beacon:surveyed' and row['success'] for row in rows),
                'resumed_after_conflict': any(row['cycle'] > 29 and row['accepted'] for row in rows),
                'pending_knowledge': loop.learning.current().knowledge == {},
                'graph_unchanged': graph_before == digest(graph_path),
                'world_facts': sorted(final.facts),
                'world_conflicts': list(final.conflicts),
                'statuses': dict(Counter(row['status'] for row in rows)),
                'objectives': dict(Counter(row['objective'] or 'none' for row in rows)),
            },
        }


def main():
    result = {name: run_environment(name) for name in ('repetition_only', 'new_opportunity', 'safety_conflict')}
    repetition = result['repetition_only']['summary']
    opportunity = result['new_opportunity']['summary']
    safety = result['safety_conflict']['summary']
    assert repetition['trajectory_reviews'] >= 1
    assert repetition['gap_reviews'] >= 1
    assert repetition['gap_hypotheses'] >= 1
    assert opportunity['trajectory_reviews'] >= 1
    assert opportunity['beacon_surveyed'] is True
    assert safety['safety_pauses'] >= 4
    assert safety['resumed_after_conflict'] is True
    assert all(row['summary']['pending_knowledge'] for row in result.values())
    assert all(row['summary']['graph_unchanged'] for row in result.values())
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({name: result[name]['summary'] for name in result}, indent=2))


if __name__ == '__main__':
    main()
