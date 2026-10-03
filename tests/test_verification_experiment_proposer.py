import hashlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from grandnexus.drive_module import DriveModule
from grandnexus.drive_policy import DrivePolicy
from grandnexus.gap_problem_solver import GapProblemSolver
from grandnexus.semantic_graph import GraphStatus, SemanticGraph
from grandnexus.symbolic_planner import SimAction
from grandnexus.verification_experiment_proposer import VerificationCapability, VerificationExperimentProposer
from grandnexus.world_state_ledger import WorldStateLedger


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def actions():
    return [
        SimAction('return_home', frozenset({'at:room'}), frozenset({'at:home'}), frozenset({'at:room'})),
        SimAction('enter_room', frozenset({'at:home'}), frozenset({'at:room'}), frozenset({'at:home'})),
        SimAction('survey_beacon', frozenset({'at:room', 'beacon:visible'}), frozenset({'beacon:surveyed'})),
        SimAction('verify_beacon_visibility', frozenset({'at:room'}), frozenset({'observation:beacon:visible'})),
    ]


def make_gap(model):
    return GapProblemSolver(model).analyze({'at:room'}, {'at:room'}, (), ('door:open', 'at:room'))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        graph_path = root / 'graph.db'
        graph = SemanticGraph(graph_path)
        agent = graph.add_node('agent', node_id='agent')
        room = graph.add_node('room', node_id='room')
        graph.relate(agent, 'at', room, GraphStatus.VALIDATED, 0.95, ('verification-test',), 'v1')
        ledger_path = root / 'world.db'
        ledger = WorldStateLedger(ledger_path)
        ledger.apply_transition('agent', {'at:room'}, (), 'test-seed')
        snapshot = ledger.snapshot('agent')
        graph_before = digest(graph_path)
        ledger_before = digest(ledger_path)

        model = actions()
        gap = make_gap(model)
        assert gap.status == 'hypotheses_available'
        capability = VerificationCapability(
            'beacon-visibility-observation',
            'beacon:visible',
            'verify_beacon_visibility',
            'observation:beacon:visible',
            'observe whether the beacon is visible without asserting visibility',
        )
        proposer = VerificationExperimentProposer(model, DrivePolicy(DriveModule(root / 'drives.db')), graph_path, (capability,))
        result = proposer.propose_and_evaluate(gap, snapshot)
        assert result.status == 'candidates_evaluated', result
        assert len(result.experiments) == 1
        experiment = result.experiments[0]
        assert experiment.status == 'shadow_simulated', experiment
        assert experiment.shadow_result and experiment.shadow_result.stable_unchanged
        output = experiment.shadow_result.candidate_output
        assert output['simulation_success'] is True
        assert output['candidate_ledger_isolated'] is True
        assert output['candidate_graph_unchanged'] is True
        assert output['observation_recorded'] is True
        assert output['probed_fact_asserted'] is False
        assert digest(graph_path) == graph_before
        assert digest(ledger_path) == ledger_before
        assert ledger.snapshot('agent').facts == frozenset({'at:room'})

        manufacturing = SimAction('verify_badly', frozenset({'at:room'}), frozenset({'beacon:visible', 'observation:beacon:visible'}))
        unsafe = VerificationCapability('bad-capability', 'beacon:visible', 'verify_badly', 'observation:beacon:visible')
        rejected = VerificationExperimentProposer(
            [*model, manufacturing], DrivePolicy(DriveModule(root / 'unsafe-drives.db')), graph_path, (unsafe,)
        ).propose_and_evaluate(gap, snapshot)
        assert rejected.status == 'candidates_rejected'
        assert rejected.experiments[0].status == 'rejected'
        assert 'manufacture' in rejected.experiments[0].reason
        assert digest(graph_path) == graph_before
        assert digest(ledger_path) == ledger_before

        high_risk = SimAction('verify_high_risk', frozenset({'at:room'}), frozenset({'observation:beacon:visible'}), risk='high')
        high_risk_capability = VerificationCapability('high-risk-capability', 'beacon:visible', 'verify_high_risk', 'observation:beacon:visible')
        risk_rejected = VerificationExperimentProposer(
            [action for action in model if action.name != 'verify_beacon_visibility'] + [high_risk],
            DrivePolicy(DriveModule(root / 'risk-drives.db')),
            graph_path,
            (high_risk_capability,),
        ).propose_and_evaluate(gap, snapshot)
        assert risk_rejected.status == 'candidates_rejected'
        assert risk_rejected.experiments[0].status == 'rejected'
        assert 'risk exceeds policy' in risk_rejected.experiments[0].reason
        assert digest(graph_path) == graph_before
        assert digest(ledger_path) == ledger_before

        ledger.apply_transition('agent', {'door:open', 'door:closed'}, (), 'test-conflict')
        blocked = proposer.propose_and_evaluate(gap, ledger.snapshot('agent'))
        assert blocked.status == 'blocked_by_conflict'
        assert blocked.experiments == ()
        assert digest(graph_path) == graph_before
        print({
            'candidate': experiment.status,
            'candidate_graph_unchanged': output['candidate_graph_unchanged'],
            'probed_fact_asserted': output['probed_fact_asserted'],
            'manufacturing_candidate': rejected.experiments[0].status,
            'high_risk_candidate': risk_rejected.experiments[0].status,
            'conflict': blocked.status,
        })


if __name__ == '__main__':
    main()
