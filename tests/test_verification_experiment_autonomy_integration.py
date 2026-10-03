import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from grandnexus.autonomy_level1 import AutonomyLevelOne
from grandnexus.drive_module import DriveModule
from grandnexus.integrated_loop import IntegratedCognitiveLoop
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction
from grandnexus.verification_experiment_proposer import VerificationCapability


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def core_actions():
    return [
        SimAction('find_key', frozenset({'at:home'}), frozenset({'has:key'})),
        SimAction('open_door', frozenset({'has:key'}), frozenset({'door:open'}), frozenset({'door:closed'})),
        SimAction('enter_room', frozenset({'at:home', 'door:open'}), frozenset({'at:room'}), frozenset({'at:home'})),
        SimAction('return_home', frozenset({'at:room'}), frozenset({'at:home'}), frozenset({'at:room'})),
        SimAction('close_door', frozenset({'at:home', 'door:open'}), frozenset({'door:closed'}), frozenset({'door:open'})),
        SimAction('survey_beacon', frozenset({'at:room', 'beacon:visible'}), frozenset({'beacon:surveyed'})),
    ]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path = root / 'graph.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        home = graph.add_node('home', node_id='home')
        graph.relate(agent, 'at', home, GraphStatus.VALIDATED, 0.95, ('verification-integration',), 'v1')
        graph_before = digest(graph_path)
        world_path = root / 'world.db'
        loop = IntegratedCognitiveLoop(graph, core_actions(), root / 'learning.db', root / 'trace.db', world_state_db=world_path)
        observation_action = SimAction(
            'verify_beacon_visibility',
            frozenset({'at:room'}),
            frozenset({'observation:beacon:visible'}),
        )
        capability = VerificationCapability(
            'beacon-visibility-observation',
            'beacon:visible',
            'verify_beacon_visibility',
            'observation:beacon:visible',
        )
        autonomy = AutonomyLevelOne(
            loop,
            DriveModule(root / 'drives.db'),
            'agent',
            verification_actions=(observation_action,),
            verification_capabilities=(capability,),
        )
        rows = [autonomy.step(cycle).to_dict() for cycle in range(1, 41)]
        reviews = [row for row in rows if row['status'] == 'trajectory_review']
        evaluated = [row for row in reviews if row['verification_status'] == 'candidates_evaluated']
        assert reviews
        assert evaluated
        assert all(row['gap_status'] == 'hypotheses_available' for row in evaluated)
        assert all('shadow simulation=True' in summary for row in evaluated for summary in row['verification_experiments'])
        assert all(row['accepted'] is False and not row['executed'] for row in evaluated)
        trace = loop.trace.cycle(f"autonomy-{evaluated[0]['cycle']:04d}")
        verification_events = [event for event in trace if event.event_type == 'verification_experiment']
        assert len(verification_events) == 1
        assert verification_events[0].status == 'candidates_evaluated'
        assert verification_events[0].payload['experiments'][0]['shadow']['stable_unchanged'] is True
        snapshot = loop.world_state.snapshot('agent')
        assert 'beacon:visible' not in snapshot.facts
        assert 'observation:beacon:visible' not in snapshot.facts
        assert graph_before == digest(graph_path)
        assert loop.learning.current().knowledge == {}
        print({
            'cycles': len(rows),
            'trajectory_reviews': len(reviews),
            'shadow_candidates': len(evaluated),
            'verification_trace_events': len(verification_events),
            'world_facts': sorted(snapshot.facts),
            'graph_unchanged': graph_before == digest(graph_path),
        })


if __name__ == '__main__':
    main()
