import hashlib
import json
from collections import Counter
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.autonomy_level1 import AutonomyLevelOne
from grandnexus.drive_module import DriveModule
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction


def digest(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def actions():
    return [
        SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
        SimAction('open_door', frozenset({'has:key'}), frozenset({'door:open'}), frozenset({'door:closed'})),
        SimAction('enter_room', frozenset({'at:home', 'door:open'}), frozenset({'at:room'}), frozenset({'at:home'})),
        SimAction('inspect_room', frozenset({'at:room'}), frozenset({'room:inspected'})),
        SimAction('collect_map', frozenset({'at:room'}), frozenset({'has:map'})),
        SimAction('return_home', frozenset({'at:room'}), frozenset({'at:home'}), frozenset({'at:room'})),
        SimAction('close_door', frozenset({'at:home', 'door:open'}), frozenset({'door:closed'}), frozenset({'door:open'})),
        SimAction('recharge', frozenset({'at:home', 'battery:low'}), frozenset({'battery:charged'}), frozenset({'battery:low'})),
        SimAction('survey_area', frozenset({'at:room', 'battery:charged'}), frozenset({'area:surveyed'})),
    ]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path = root / 'graph.db'
        world_path = root / 'world.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        charged = graph.add_node('charged', node_id='charged')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('autonomy-seed',), 'v1')
        graph.relate(agent, 'battery', charged, GraphStatus.VALIDATED, 0.90, ('autonomy-seed',), 'v1')
        graph_before = digest(graph_path)

        def build(_suffix: str):
            loop = IntegratedCognitiveLoop(
                graph,
                actions(),
                root / 'learning.db',
                root / 'trace.db',
                world_state_db=world_path,
            )
            return loop, AutonomyLevelOne(loop, DriveModule(root / 'drives.db'), 'agent')

        loop, autonomy = build('a')
        rows = []
        perturbations = []
        for cycle in range(1, 121):
            if cycle == 25:
                loop.world_state.apply_transition('agent', {'battery:low'}, {'battery:charged'}, 'environment-perturbation', 'perturbation:low-battery')
                perturbations.append({'cycle': cycle, 'type': 'battery_low'})
            elif cycle == 50:
                snap = loop.world_state.snapshot('agent')
                removals = {fact for fact in snap.facts if fact.startswith('at:')}
                loop.world_state.apply_transition('agent', {'at:unknown'}, removals, 'environment-perturbation', 'perturbation:unknown-location')
                perturbations.append({'cycle': cycle, 'type': 'unknown_location'})
            elif cycle == 55:
                loop.world_state.apply_transition('agent', {'at:home'}, {'at:unknown'}, 'environment-recovery', 'perturbation:return-home')
                perturbations.append({'cycle': cycle, 'type': 'restore_location'})
            elif cycle == 80:
                current = loop.world_state.snapshot('agent')
                additions = {'door:open', 'door:closed'}
                loop.world_state.apply_transition('agent', additions, (), 'environment-perturbation', 'perturbation:door-conflict')
                perturbations.append({'cycle': cycle, 'type': 'door_conflict'})
            elif cycle == 84:
                loop.world_state.apply_transition('agent', (), {'door:open', 'door:closed'}, 'environment-recovery', 'perturbation:resolve-door')
                perturbations.append({'cycle': cycle, 'type': 'resolve_door_conflict'})
            elif cycle == 61:
                loop.world_state.close()
                loop, autonomy = build('b')
                perturbations.append({'cycle': cycle, 'type': 'process_restart'})

            result = autonomy.step(cycle)
            rows.append(result.to_dict())

        graph_after = digest(graph_path)
        final_snapshot = loop.world_state.snapshot('agent')
        review = loop.meta.review()
        objective_counts = Counter(row['objective'] or 'none' for row in rows)
        executed_counts = Counter(action for row in rows for action in row['executed'])
        status_counts = Counter(row['status'] for row in rows)
        reasons = Counter(row['reason'] for row in rows)
        proposals = [row['learning_proposal_id'] for row in rows if row['learning_proposal_id']]
        transitions = loop.world_state.history('agent')
        repeated_pairs = Counter((rows[i - 1]['objective'], rows[i]['objective']) for i in range(1, len(rows)))
        dominant_pair, dominant_pair_count = repeated_pairs.most_common(1)[0]
        result = {
            'configuration': {
                'cycles': 120,
                'modules_disabled': ['llm', 'embeddings', 'multiagent', 'external_actions'],
                'goal_sequence_supplied': False,
                'objective_source': 'DriveModule + symbolic action affordances',
                'restart_cycle': 61,
            },
            'summary': {
                'accepted': sum(1 for row in rows if row['accepted']),
                'successful_simulations': sum(1 for row in rows if row['success'] is True),
                'idle_or_blocked': sum(1 for row in rows if row['objective'] is None),
                'failed_or_rejected': sum(1 for row in rows if row['success'] is False or (row['objective'] and not row['accepted'])),
                'learning_proposals_pending': len(proposals),
                'automatic_promotions': 0,
                'world_state_revision': final_snapshot.revision,
                'world_state_conflicts': list(final_snapshot.conflicts),
                'world_state_facts': sorted(final_snapshot.facts),
                'world_state_events_after_restart_visible': len(transitions),
                'graph_unchanged': graph_before == graph_after,
                'metacognition': {'count_since_restart': review.count, 'accuracy': review.accuracy, 'mean_confidence': review.mean_confidence},
                'dominant_transition_pair': list(dominant_pair),
                'dominant_transition_pair_count': dominant_pair_count,
            },
            'objective_counts': dict(objective_counts),
            'executed_counts': dict(executed_counts),
            'status_counts': dict(status_counts),
            'reason_counts': dict(reasons),
            'perturbations': perturbations,
            'cycles': rows,
            'graph_before': graph_before,
            'graph_after': graph_after,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        assert len(rows) == 120
        assert graph_before == graph_after
        assert final_snapshot.revision > 0
        assert any(row['status'] == 'verification_first' for row in rows)
        assert all(row['status'] != 'approval_required' for row in rows)
        assert loop.learning.current().knowledge == {}


if __name__ == '__main__':
    main()
