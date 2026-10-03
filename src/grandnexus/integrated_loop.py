"""End-to-end bounded cognitive loop for GrandNexus."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .advanced_planner import AdvancedPlanner
from .failure_events import FailureRegistry
from .graph_planner import GraphPlanner
from .learning_controller import LearningController
from .learning_experiment import LearningProposal, SlowLearningStore
from .metacognition_loop import MetacognitionLoop
from .observability import TraceLog
from .semantic_graph import SemanticGraph
from .episodic_context import LocalEpisodicContext
from .symbolic_planner import SimAction, SimulationResult
from .world_state_ledger import WorldStateLedger


@dataclass(frozen=True)
class LoopResult:
    accepted: bool
    prediction_id: str
    simulation: SimulationResult | None
    reason: str


class IntegratedCognitiveLoop:
    def __init__(self, graph: SemanticGraph, actions: Iterable[SimAction], learning_db: str | Path, trace_db: str | Path | None = None, world_state_db: str | Path | None = None, enable_world_state: bool = True):
        actions = list(actions)
        self.graph_planner = GraphPlanner(graph, actions)
        self.failures = FailureRegistry()
        self.trace = TraceLog(trace_db or learning_db)
        self.advanced_planner = AdvancedPlanner(actions, max_risk='medium')
        self.meta = MetacognitionLoop()
        self.learning = SlowLearningStore(learning_db)
        self.learning_controller = LearningController(self.meta, self.learning, min_observations=3)
        # Local episodic integration is deterministic, optional in spirit, and
        # never promotes simulation facts to semantic truth by itself.
        self.episodic_context = LocalEpisodicContext()
        ledger_path = world_state_db or f"{learning_db}.world_state.db"
        self.world_state = WorldStateLedger(ledger_path) if enable_world_state else None

    def _required_preconditions(self, objectives: Iterable[str]) -> set[str]:
        actions = self.advanced_planner.planner.actions
        required: set[str] = set()
        frontier = list(objectives)
        seen: set[str] = set()
        while frontier:
            goal = frontier.pop()
            if goal in seen:
                continue
            seen.add(goal)
            for action in actions:
                if goal in action.effects:
                    for precondition in action.preconditions:
                        required.add(precondition)
                        frontier.append(precondition)
        return required

    def run(self, node_id: str, objectives: Iterable[str], expected_success: bool = True, request_id: str = 'integrated') -> LoopResult:
        objectives = tuple(objectives)
        context = self.graph_planner.context_for(node_id)
        required_effects = self._required_preconditions(objectives)
        if self.world_state is not None:
            ledger_snapshot = self.world_state.snapshot(node_id)
            if ledger_snapshot.revision == 0 and context.state:
                self.world_state.apply_transition(node_id, context.state, (), 'semantic-graph-seed')
                ledger_snapshot = self.world_state.snapshot(node_id)
            active_state = set(ledger_snapshot.facts)
            recall = self.episodic_context.recall(objectives, required_effects, active_state)
            planning_state = active_state
            planning_conflicts = ledger_snapshot.conflicts
        else:
            ledger_snapshot = None
            recall = self.episodic_context.recall(objectives, required_effects, context.state)
            planning_state = set(context.state) | set(recall.recalled_state)
            planning_conflicts = recall.conflicts
        self.trace.record(request_id, 'retrieval', 'graph_context_loaded', 'completed', None, context.validated_relation_ids, {'contradictions': context.contradiction_relation_ids, 'state_size': len(context.state), 'world_state_revision': ledger_snapshot.revision if ledger_snapshot else None, 'world_state_size': len(ledger_snapshot.facts) if ledger_snapshot else None, 'world_state_conflicts': ledger_snapshot.conflicts if ledger_snapshot else (), 'episodic_state_size': len(recall.recalled_state), 'episodic_episode_ids': recall.episode_ids, 'required_effects': tuple(sorted(required_effects)), 'episodic_conflicts': recall.conflicts, 'suppressed_effects': recall.suppressed_effects})
        decision = self.advanced_planner.plan_compound(objectives, planning_state, request_id, planning_conflicts)
        self.trace.record(request_id, 'planning', 'plan_decision', 'accepted' if decision.accepted else 'rejected', 1.0 if decision.accepted else 0.0, (), {'reason': decision.reason, 'risk': decision.risk, 'objectives': decision.objectives})
        confidence = 1.0 if decision.accepted else 0.0
        prediction_id = self.meta.register(confidence, {'request_id': request_id, 'objectives': tuple(objectives)})
        if not decision.accepted or decision.plan is None:
            category = 'unreachable_objective' if 'not reachable' in decision.reason else 'rejected_before_plan'
            self.failures.record(category, decision.reason, {'request_id': request_id})
            self.trace.record(request_id, 'planning', category, 'rejected', confidence, (), {'reason': decision.reason})
            self.meta.observe(prediction_id, not expected_success)
            self.episodic_context.record(request_id, objectives, planning_state, None, expected_success)
            return LoopResult(False, prediction_id, None, decision.reason)
        simulation = self.graph_planner.planner.simulate(decision.plan, planning_state)
        self.trace.record(request_id, 'simulation', 'plan_simulated', 'completed' if simulation.success else 'failed', confidence, (), {'executed': simulation.executed, 'failed_step': simulation.failed_step, 'message': simulation.message})
        if not simulation.success:
            self.failures.record('simulation_failure', simulation.message or 'simulation failed', {'request_id': request_id, 'failed_step': simulation.failed_step})
        self.meta.observe(prediction_id, simulation.success == expected_success)
        episode_id = self.episodic_context.record(request_id, objectives, planning_state, simulation, expected_success)
        world_state_revision = None
        if self.world_state is not None and simulation.success:
            world_state_revision = self.world_state.apply_transition(
                node_id,
                set(simulation.final_state) - planning_state,
                planning_state - set(simulation.final_state),
                'simulation-observation',
                episode_id,
            )
        self.trace.record(request_id, 'metacognition', 'outcome_observed', 'completed', confidence, (prediction_id,), {'expected_success': expected_success, 'actual_success': simulation.success, 'correct': simulation.success == expected_success, 'episodic_memory_size': self.episodic_context.size(), 'world_state_revision': world_state_revision})
        if simulation.success != expected_success:
            self.failures.record('prediction_error', 'predicted outcome differs from simulation', {'request_id': request_id})
        return LoopResult(simulation.success, prediction_id, simulation, 'simulation completed' if simulation.success else simulation.message)

    def propose_learning(self, change: dict, hypothesis: str) -> LearningProposal | None:
        proposal = self.learning_controller.propose_if_ready(change, hypothesis)
        self.trace.record('learning', 'learning', 'proposal_created' if proposal else 'proposal_deferred', 'pending' if proposal else 'completed', None, (), {'hypothesis': hypothesis, 'proposal_id': proposal.proposal_id if proposal else None})
        return proposal
