from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .drive_module import DriveModule, DriveSignal
from .drive_policy import DrivePolicy
from .integrated_loop import IntegratedCognitiveLoop
from .trajectory_metacognition import TrajectoryAssessment, TrajectoryMetacognition
from .gap_problem_solver import GapProblemSolver
from .symbolic_planner import SimAction
from .verification_experiment_proposer import VerificationCapability, VerificationExperimentProposer


@dataclass(frozen=True)
class AutonomousCycle:
    cycle: int
    status: str
    selected_drive: str | None
    objective: str | None
    priority_ranking: tuple[tuple[str, float], ...]
    accepted: bool
    success: bool | None
    executed: tuple[str, ...]
    reason: str
    state_revision_before: int
    state_revision_after: int
    conflicts: tuple[tuple[str, str], ...]
    degraded_mode: bool = False
    learning_proposal_id: str | None = None
    trajectory_status: str = 'normal'
    trajectory_novelty: float = 0.0
    trajectory_reason: str = ''
    gap_status: str = 'not_applicable'
    gap_hypotheses: tuple[str, ...] = ()
    verification_status: str = 'not_applicable'
    verification_experiments: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutonomyLevelOne:
    """Drive-led autonomy inside simulation.

    No caller supplies a target sequence. The agent derives candidate objectives
    from currently applicable symbolic actions and its internal drive signals.
    External effects, stable-graph mutations and automatic promotions remain out
    of scope.
    """

    def __init__(
        self,
        loop: IntegratedCognitiveLoop,
        drives: DriveModule,
        node_id: str,
        trajectory: TrajectoryMetacognition | None = None,
        verification_actions: tuple[SimAction, ...] = (),
        verification_capabilities: tuple[VerificationCapability, ...] = (),
    ):
        if loop.world_state is None:
            raise ValueError('AutonomyLevelOne requires WorldStateLedger')
        self.loop = loop
        self.drives = drives
        self.node_id = node_id
        self.policy = DrivePolicy(drives)
        self.trajectory = trajectory or TrajectoryMetacognition()
        self.gap_solver = GapProblemSolver(self.actions)
        self.verification_proposer = VerificationExperimentProposer(
            (*self.actions, *verification_actions),
            self.policy,
            self.loop.graph_planner.graph.db_file,
            verification_capabilities,
        )
        self._attempts: dict[str, int] = {}
        for name, weight in (
            ('safety_check', 1.2),
            ('goal_progress', 1.0),
            ('knowledge_gap', 0.9),
            ('memory_maintenance', 0.6),
            ('trajectory_review', 1.1),
        ):
            if name not in self.drives.drives:
                self.drives.register_drive(name, weight)

    @property
    def actions(self):
        return self.loop.advanced_planner.planner.actions

    def _actionable(self, state: set[str]):
        candidates = []
        for action in self.actions:
            novel_effects = sorted(set(action.effects) - state)
            if action.preconditions <= state and novel_effects:
                candidates.append((action, novel_effects))
        return sorted(candidates, key=lambda item: (self._attempts.get(item[0].name, 0), item[0].risk, item[0].name))

    def _blocked_missing(self, state: set[str]):
        rows = []
        producible = {effect for action in self.actions for effect in action.effects}
        for action in self.actions:
            if set(action.effects) <= state:
                continue
            missing = sorted(set(action.preconditions) - state)
            for fact in missing:
                rows.append((0 if fact in producible else 1, self._attempts.get(action.name, 0), action.name, fact))
        return sorted(rows)

    def _signals(self, state: set[str], conflicts: tuple[tuple[str, str], ...], cycle: int, assessment: TrajectoryAssessment) -> list[DriveSignal]:
        actionable = self._actionable(state)
        blocked = self._blocked_missing(state)
        return [
            DriveSignal('safety_check', 1.0 if conflicts else 0.05, 1.0 if conflicts else 0.0, 1.0, {'conflicts': conflicts}),
            DriveSignal('goal_progress', 0.9 if actionable else 0.15, 0.55 if actionable else 0.1, 0.9 if actionable else 0.2, {'actionable': len(actionable)}),
            DriveSignal('knowledge_gap', 0.8 if not actionable and blocked else 0.25, 0.45 if blocked else 0.1, 0.35 if blocked else 0.8, {'blocked': len(blocked)}),
            DriveSignal('memory_maintenance', 0.65 if cycle % 10 == 0 else 0.15, 0.3, 0.8, {'cycle': cycle}),
            DriveSignal('trajectory_review', 1.0 if assessment.status == 'stagnating' else 0.0, 0.8 if assessment.status == 'stagnating' else 0.0, 0.9, {'trajectory': assessment.status, 'novelty': assessment.novelty, 'pattern': assessment.repeated_pattern}),
        ]

    def _objective_for(self, selected_drive: str | None, state: set[str]) -> tuple[str | None, str | None]:
        if selected_drive == 'goal_progress':
            actionable = self._actionable(state)
            if actionable:
                action, novel_effects = actionable[0]
                return novel_effects[0], action.name
        if selected_drive == 'knowledge_gap':
            blocked = self._blocked_missing(state)
            if blocked:
                _unknown, _attempts, action_name, fact = blocked[0]
                return fact, action_name
        return None, None

    def step(self, cycle: int) -> AutonomousCycle:
        before = self.loop.world_state.snapshot(self.node_id)
        if before.revision == 0:
            graph_context = self.loop.graph_planner.context_for(self.node_id)
            if graph_context.state:
                self.loop.world_state.apply_transition(self.node_id, graph_context.state, (), 'semantic-graph-seed')
                before = self.loop.world_state.snapshot(self.node_id)
        state = set(before.facts)
        actionable = self._actionable(state)
        candidate_objectives = [effect for _action, effects in actionable for effect in effects]
        assessment = self.trajectory.assess(candidate_objectives, state)
        signals = self._signals(state, before.conflicts, cycle, assessment)
        resolution = self.policy.resolve(
            signals,
            contradiction=bool(before.conflicts),
            external_effect=False,
            risk='low',
            reversible=True,
            simulation_only=True,
        )
        objective, action_name = self._objective_for(resolution.selected_drive, state)
        if resolution.selected_drive == 'trajectory_review' and assessment.status == 'stagnating':
            self.trajectory.mark_reflective_pause()
            selected_signal = next(signal for signal in signals if signal.drive == 'trajectory_review')
            self.drives.propose(selected_signal, 'review:trajectory')
            gap_analysis = self.gap_solver.analyze(
                state,
                self.trajectory.seen_facts,
                before.conflicts,
                assessment.repeated_pattern,
            )
            gap_summaries = tuple(hypothesis.verification_question for hypothesis in gap_analysis.hypotheses)
            verification = self.verification_proposer.propose_and_evaluate(gap_analysis, before)
            verification_summaries = tuple(experiment.summary for experiment in verification.experiments)
            self.loop.trace.record(
                f'autonomy-{cycle:04d}', 'trajectory_review', 'gap_analysis', gap_analysis.status,
                None, (), {'reason': gap_analysis.reason, 'hypotheses': gap_summaries},
            )
            self.loop.trace.record(
                f'autonomy-{cycle:04d}', 'trajectory_review', 'verification_experiment', verification.status,
                None, (), verification.trace_payload(),
            )
            proposal = self.loop.propose_learning(
                {'trajectory_review': {
                    'pattern': assessment.repeated_pattern,
                    'repetitions': assessment.pattern_repetitions,
                    'novelty': assessment.novelty,
                    'gap_status': gap_analysis.status,
                    'gap_hypotheses': gap_summaries,
                    'verification_status': verification.status,
                    'verification_experiments': verification_summaries,
                }},
                f'low-information repeated trajectory {assessment.repeated_pattern} observed {assessment.pattern_repetitions} times; {gap_analysis.reason}',
            )
            return AutonomousCycle(
                cycle, 'trajectory_review', resolution.selected_drive, None, resolution.ranked,
                False, None, (), assessment.reason, before.revision, before.revision,
                before.conflicts, learning_proposal_id=proposal.proposal_id if proposal else None,
                trajectory_status=assessment.status, trajectory_novelty=assessment.novelty, trajectory_reason=assessment.reason,
                gap_status=gap_analysis.status, gap_hypotheses=gap_summaries,
                verification_status=verification.status, verification_experiments=verification_summaries,
            )
        if objective is None:
            return AutonomousCycle(
                cycle, resolution.status, resolution.selected_drive, None, resolution.ranked,
                False, None, (), resolution.reason, before.revision, before.revision,
                before.conflicts, trajectory_status=assessment.status, trajectory_novelty=assessment.novelty, trajectory_reason=assessment.reason,
            )
        selected_signal = next(signal for signal in signals if signal.drive == resolution.selected_drive)
        self.drives.propose(selected_signal, objective)
        self._attempts[action_name or objective] = self._attempts.get(action_name or objective, 0) + 1
        result = self.loop.run(self.node_id, [objective], request_id=f'autonomy-{cycle:04d}')
        proposal_id = None
        observation_count = self._attempts.get(action_name or objective, 0)
        if result.accepted and result.simulation and result.simulation.success and observation_count in {3, 6, 12}:
            proposal = self.loop.propose_learning(
                {'autonomy_preference': {'action': action_name, 'effect': objective, 'observations': observation_count}},
                f'repeated simulated transition {action_name} -> {objective} observed {observation_count} times',
            )
            proposal_id = proposal.proposal_id if proposal else None
        after = self.loop.world_state.snapshot(self.node_id)
        self.trajectory.observe(objective, before.facts, after.facts)
        return AutonomousCycle(
            cycle,
            resolution.status,
            resolution.selected_drive,
            objective,
            resolution.ranked,
            result.accepted,
            result.simulation.success if result.simulation else None,
            result.simulation.executed if result.simulation else (),
            result.reason,
            before.revision,
            after.revision,
            after.conflicts,
            learning_proposal_id=proposal_id,
            trajectory_status=assessment.status,
            trajectory_novelty=assessment.novelty,
            trajectory_reason=assessment.reason,
        )
