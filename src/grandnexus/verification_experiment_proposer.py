"""Propose and shadow-evaluate safe symbolic verification experiments.

A verification experiment may model an observation, but it must never manufacture
its probed fact. It operates from a WorldStateLedger snapshot and writes only to
a temporary ledger inside a ShadowCycle.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import tempfile
from typing import Iterable

from .advanced_planner import AdvancedPlanner
from .drive_module import DriveSignal
from .drive_policy import DrivePolicy
from .gap_problem_solver import GapAnalysis, GapHypothesis
from .shadow_cycle import ShadowCycle, ShadowResult
from .symbolic_planner import SimAction
from .world_state_ledger import WorldStateLedger, WorldStateSnapshot


@dataclass(frozen=True)
class VerificationCapability:
    """An explicit symbolic action that can gather an observation in simulation."""

    capability_id: str
    probes_fact: str
    action_name: str
    observation_effect: str
    description: str = ''

    def __post_init__(self) -> None:
        if not self.capability_id.strip() or not self.probes_fact.strip() or not self.action_name.strip():
            raise ValueError('verification capability fields must be non-empty')
        if not self.observation_effect.startswith('observation:'):
            raise ValueError('verification observations must use the observation: namespace')


@dataclass(frozen=True)
class VerificationExperiment:
    """A candidate experiment and its isolated simulation result, if any."""

    experiment_id: str
    gap_id: str
    probes_fact: str
    observation_effect: str
    action_name: str
    plan_steps: tuple[str, ...]
    state_revision: int
    risk: str
    status: str
    reason: str
    shadow_result: ShadowResult | None = None

    @property
    def summary(self) -> str:
        if self.shadow_result is None:
            return f'{self.action_name} for {self.probes_fact}: {self.status} ({self.reason})'
        simulated = self.shadow_result.candidate_output.get('simulation_success')
        return f'{self.action_name} for {self.probes_fact}: {self.status}; shadow simulation={simulated}'

    def trace_payload(self) -> dict:
        payload = {
            'experiment_id': self.experiment_id,
            'gap_id': self.gap_id,
            'probes_fact': self.probes_fact,
            'observation_effect': self.observation_effect,
            'action_name': self.action_name,
            'plan_steps': self.plan_steps,
            'state_revision': self.state_revision,
            'risk': self.risk,
            'status': self.status,
            'reason': self.reason,
        }
        if self.shadow_result is not None:
            payload['shadow'] = {
                'status': self.shadow_result.status,
                'stable_unchanged': self.shadow_result.stable_unchanged,
                'candidate_output': self.shadow_result.candidate_output,
            }
        return payload


@dataclass(frozen=True)
class VerificationProposalSet:
    status: str
    experiments: tuple[VerificationExperiment, ...]
    reason: str

    def trace_payload(self) -> dict:
        return {
            'status': self.status,
            'reason': self.reason,
            'experiments': [experiment.trace_payload() for experiment in self.experiments],
        }


class VerificationExperimentProposer:
    """Translates gaps into declared, shadow-only verification candidates.

    This class receives a snapshot, never a mutable stable ledger. Candidate
    simulation seeds a new temporary WorldStateLedger. The stable graph is copied
    by ShadowCycle and is not available for mutation through this interface.
    """

    _SAFETY_ACCEPTED = frozenset({'progress_allowed', 'simulation_allowed_with_review'})

    def __init__(
        self,
        actions: Iterable[SimAction],
        drive_policy: DrivePolicy,
        stable_graph_db: str | Path,
        capabilities: Iterable[VerificationCapability] = (),
        max_risk: str = 'medium',
    ):
        self.actions = tuple(actions)
        self.actions_by_name = {action.name: action for action in self.actions}
        self.drive_policy = drive_policy
        self.shadow_cycle = ShadowCycle(stable_graph_db)
        self.capabilities = tuple(capabilities)
        self.capabilities_by_fact: dict[str, tuple[VerificationCapability, ...]] = {}
        for capability in self.capabilities:
            self.capabilities_by_fact.setdefault(capability.probes_fact, ())
            self.capabilities_by_fact[capability.probes_fact] += (capability,)
        self.planner = AdvancedPlanner(self.actions, max_risk=max_risk)

    def _rejected(self, gap: GapHypothesis, capability: VerificationCapability, snapshot: WorldStateSnapshot, reason: str, risk: str = 'low') -> VerificationExperiment:
        return VerificationExperiment(
            f'verification:{gap.gap_id}:{capability.capability_id}',
            gap.gap_id,
            capability.probes_fact,
            capability.observation_effect,
            capability.action_name,
            (),
            snapshot.revision,
            risk,
            'rejected',
            reason,
        )

    @staticmethod
    def _capability_error(capability: VerificationCapability, action: SimAction | None) -> str | None:
        if action is None:
            return 'declared verification action is absent from the symbolic action model'
        if capability.observation_effect not in action.effects:
            return 'declared verification action does not produce its declared observation effect'
        if capability.probes_fact in action.effects or capability.probes_fact in action.deletes:
            return 'verification action would manufacture or remove its probed fact'
        if action.deletes:
            return 'verification action must not delete current-state facts'
        if any(not effect.startswith('observation:') for effect in action.effects):
            return 'verification action may only produce observation:* effects'
        return None

    def _shadow_evaluate(self, experiment: VerificationExperiment, plan, snapshot: WorldStateSnapshot) -> ShadowResult:
        state = set(snapshot.facts)

        def candidate(candidate_graph_db: Path) -> dict:
            graph_before = hashlib.sha256(candidate_graph_db.read_bytes()).hexdigest()
            with tempfile.TemporaryDirectory(prefix='grandnexus-verification-ledger-') as tmp:
                ledger = WorldStateLedger(Path(tmp) / 'candidate_world.db')
                ledger.apply_transition('verification-shadow', state, (), 'verification-shadow-seed')
                simulation = self.planner.planner.simulate(plan, state)
                if simulation.success:
                    ledger.apply_transition(
                        'verification-shadow',
                        set(simulation.final_state) - state,
                        state - set(simulation.final_state),
                        'verification-shadow-simulation',
                        experiment.experiment_id,
                    )
                candidate_snapshot = ledger.snapshot('verification-shadow')
                history_size = len(ledger.history('verification-shadow'))
                ledger.close()
            graph_after = hashlib.sha256(candidate_graph_db.read_bytes()).hexdigest()
            return {
                'simulation_success': simulation.success,
                'executed': list(simulation.executed),
                'failed_step': simulation.failed_step,
                'message': simulation.message,
                'candidate_state_facts': sorted(candidate_snapshot.facts),
                'candidate_state_conflicts': list(candidate_snapshot.conflicts),
                'candidate_state_revision': candidate_snapshot.revision,
                'candidate_ledger_history_size': history_size,
                'candidate_ledger_isolated': True,
                'candidate_graph_unchanged': graph_before == graph_after,
                'probed_fact_asserted': experiment.probes_fact in candidate_snapshot.facts,
                'observation_recorded': experiment.observation_effect in candidate_snapshot.facts,
            }

        return self.shadow_cycle.run(candidate)

    def _evaluate(self, gap: GapHypothesis, capability: VerificationCapability, snapshot: WorldStateSnapshot) -> VerificationExperiment:
        action = self.actions_by_name.get(capability.action_name)
        error = self._capability_error(capability, action)
        if error:
            return self._rejected(gap, capability, snapshot, error, action.risk if action else 'low')
        if capability.probes_fact not in gap.missing_facts:
            return self._rejected(gap, capability, snapshot, 'capability does not correspond to this symbolic gap', action.risk)
        if capability.probes_fact in snapshot.facts:
            return self._rejected(gap, capability, snapshot, 'probed fact is already present in the current state', action.risk)
        if capability.observation_effect in snapshot.facts:
            return self._rejected(gap, capability, snapshot, 'declared observation is already present in the current state', action.risk)

        request_id = f'verification-plan:{gap.gap_id}:{capability.capability_id}'
        decision = self.planner.plan_compound(
            (capability.observation_effect,),
            set(snapshot.facts),
            request_id,
            snapshot.conflicts,
        )
        if not decision.accepted or decision.plan is None:
            return self._rejected(gap, capability, snapshot, f'planner rejected candidate: {decision.reason}', decision.risk)
        plan_steps = tuple(step.step_id for step in decision.plan.steps)
        if capability.action_name not in plan_steps:
            return self._rejected(gap, capability, snapshot, 'candidate plan omits the declared verification action', decision.risk)
        plan_actions = [self.actions_by_name[step] for step in plan_steps]
        if any(capability.probes_fact in action.effects or capability.probes_fact in action.deletes for action in plan_actions):
            return self._rejected(gap, capability, snapshot, 'candidate plan would manufacture or remove its probed fact', decision.risk)

        signal = DriveSignal(
            'verification_experiment',
            0.6,
            0.5,
            0.95,
            {'gap_id': gap.gap_id, 'probes_fact': capability.probes_fact, 'plan_steps': plan_steps},
        )
        safety = self.drive_policy.resolve(
            [signal],
            external_effect=False,
            risk=decision.risk,
            reversible=True,
            contradiction=bool(snapshot.conflicts),
            simulation_only=True,
        )
        if safety.status not in self._SAFETY_ACCEPTED:
            return self._rejected(gap, capability, snapshot, f'drive policy rejected candidate: {safety.reason}', decision.risk)

        pending = VerificationExperiment(
            f'verification:{gap.gap_id}:{capability.capability_id}',
            gap.gap_id,
            capability.probes_fact,
            capability.observation_effect,
            capability.action_name,
            plan_steps,
            snapshot.revision,
            decision.risk,
            'pending_shadow',
            'candidate passed ledger snapshot, planner, and drive-policy checks',
        )
        shadow = self._shadow_evaluate(pending, decision.plan, snapshot)
        if shadow.status != 'completed' or not shadow.stable_unchanged:
            return replace(pending, status='shadow_failed', reason='shadow evaluation did not preserve the stable graph', shadow_result=shadow)
        output = shadow.candidate_output
        if not output.get('candidate_ledger_isolated') or not output.get('candidate_graph_unchanged'):
            return replace(pending, status='shadow_failed', reason='candidate isolation invariant failed', shadow_result=shadow)
        if output.get('probed_fact_asserted'):
            return replace(pending, status='shadow_failed', reason='candidate simulation asserted the probed fact', shadow_result=shadow)
        return replace(pending, status='shadow_simulated', reason='candidate evaluated only in isolated symbolic simulation', shadow_result=shadow)

    def propose_and_evaluate(self, analysis: GapAnalysis, snapshot: WorldStateSnapshot) -> VerificationProposalSet:
        if snapshot.conflicts or analysis.status == 'blocked_by_conflict':
            return VerificationProposalSet('blocked_by_conflict', (), 'current-state conflict prevents verification experiments')
        if analysis.status != 'hypotheses_available' or not analysis.hypotheses:
            return VerificationProposalSet('not_applicable', (), 'no symbolic gap hypothesis is available for verification')

        experiments: list[VerificationExperiment] = []
        for gap in analysis.hypotheses:
            for fact in gap.missing_facts:
                for capability in self.capabilities_by_fact.get(fact, ()):
                    experiments.append(self._evaluate(gap, capability, snapshot))
        if not experiments:
            return VerificationProposalSet('no_declared_capability', (), 'no declared observation capability matches the symbolic gap')
        evaluated = tuple(experiments)
        if any(item.status == 'shadow_simulated' for item in evaluated):
            return VerificationProposalSet('candidates_evaluated', evaluated, 'one or more verification candidates completed in shadow simulation')
        return VerificationProposalSet('candidates_rejected', evaluated, 'all matching verification candidates were rejected before or during shadow simulation')
