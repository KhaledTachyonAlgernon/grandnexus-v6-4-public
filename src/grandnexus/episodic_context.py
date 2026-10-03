from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .memory.episodic import EpisodicMemory, EpisodicMemoryConfig, EpisodicQuery, EpisodeType, RetrievalMode
from .symbolic_planner import SimulationResult


@dataclass(frozen=True)
class EpisodicRecall:
    recalled_state: frozenset[str]
    episode_ids: tuple[str, ...]
    event_count: int
    conflicts: tuple[tuple[str, str], ...] = ()
    suppressed_effects: tuple[str, ...] = ()


class LocalEpisodicContext:
    """Small, deterministic bridge from episodic memory to symbolic planning.

    It stores execution episodes and recalls only explicitly observed final-state
    facts. It does not promote them to semantic truth and does not use embeddings.
    """

    def __init__(self, memory: EpisodicMemory | None = None):
        self.memory = memory or EpisodicMemory(EpisodicMemoryConfig(
            embedding_function=None,
            enable_predictive_coding=False,
            enable_temporal_pooling=False,
            auto_tagging=False,
            auto_generate_summaries=False,
            consolidation_scheduler="periodic",
        ))
        self.effect_index: dict[str, set[str]] = {}
        self.episode_requirements: dict[str, frozenset[str]] = {}
        self.effect_validity: dict[tuple[str, str], bool] = {}
        self.incompatibilities: dict[str, set[str]] = {}
        for left, right in (
            ("door:open", "door:closed"),
            ("gate:open", "gate:closed"),
            ("system:active", "system:stopped"),
            ("object:present", "object:absent"),
        ):
            self.register_incompatibility(left, right)

    def register_incompatibility(self, left: str, right: str) -> None:
        if left == right:
            return
        self.incompatibilities.setdefault(left, set()).add(right)
        self.incompatibilities.setdefault(right, set()).add(left)

    def _contexts_overlap(self, older: frozenset[str], newer: frozenset[str]) -> bool:
        older_locations = {fact for fact in older if fact.startswith("at:")}
        newer_locations = {fact for fact in newer if fact.startswith("at:")}
        if older_locations and newer_locations and older_locations.isdisjoint(newer_locations):
            return False
        return True

    def recall(self, objectives: Iterable[str], required_effects: Iterable[str] = (), current_state: Iterable[str] = (), max_results: int = 8, min_activation: float = 0.2) -> EpisodicRecall:
        targets = set(required_effects)
        current = set(current_state)
        candidate_ids = set()
        for effect in targets:
            candidate_ids.update(self.effect_index.get(effect, set()))
            for incompatible_effect in self.incompatibilities.get(effect, set()):
                candidate_ids.update(self.effect_index.get(incompatible_effect, set()))
        episodes = [self.memory.episodes[eid] for eid in candidate_ids if eid in self.memory.episodes]
        episodes.sort(key=lambda ep: (ep.activation, ep.importance, ep.last_access_time), reverse=True)
        state: set[str] = set()
        provenance: dict[str, str] = {}
        selected = []
        suppressed: set[str] = set()
        conflicts: set[tuple[str, str]] = set()
        event_count = 0
        for episode in episodes[:max_results]:
            if episode.activation < min_activation:
                continue
            requirements = self.episode_requirements.get(episode.episode_id, frozenset())
            if not requirements <= current:
                continue
            selected.append(episode)
            event_count += len(episode.events)
            for event in episode.events:
                if event.metadata.get("kind") != "observed_final_state" or not event.metadata.get("reusable", False):
                    continue
                delta_added = set(episode.context.get("delta_added", ()))
                for fact in delta_added:
                    if not self.effect_validity.get((episode.episode_id, fact), True):
                        suppressed.add(fact)
                        continue
                    incompatible = self.incompatibilities.get(fact, set())
                    current_conflicts = incompatible & current
                    if current_conflicts:
                        suppressed.add(fact)
                        continue
                    recalled_conflicts = incompatible & state
                    if recalled_conflicts:
                        for other in recalled_conflicts:
                            conflicts.add(tuple(sorted((fact, other))))
                            state.discard(other)
                            provenance.pop(other, None)
                        suppressed.add(fact)
                        continue
                    state.add(fact)
                    provenance[fact] = episode.episode_id
        return EpisodicRecall(
            frozenset(state),
            tuple(ep.episode_id for ep in selected),
            event_count,
            tuple(sorted(conflicts)),
            tuple(sorted(suppressed)),
        )

    def record(self, request_id: str, objectives: Iterable[str], initial_state: Iterable[str], simulation: SimulationResult | None, expected_success: bool) -> str:
        initial = frozenset(initial_state)
        episode = self.memory.create_episode(
            EpisodeType.DECISION,
            context={"request_id": request_id, "objectives": tuple(objectives), "expected_success": expected_success, "initial_state": tuple(sorted(initial))},
            tags={"decision", "simulation"},
            episode_id=f"episode:{request_id}",
            importance=0.6 if simulation and simulation.success else 0.4,
        )
        self.memory.add_event(
            episode.episode_id,
            {"kind": "initial_state", "facts": tuple(sorted(set(initial_state)))},
            metadata={"kind": "initial_state", "reusable": False},
            importance=0.5,
        )
        if simulation is not None:
            self.memory.add_event(
                episode.episode_id,
                {"kind": "observed_final_state", "facts": tuple(sorted(simulation.final_state)), "success": simulation.success},
                metadata={"kind": "observed_final_state", "facts": tuple(sorted(simulation.final_state)), "reusable": bool(simulation.success), "validated_by": "simulation"},
                importance=0.7 if simulation.success else 0.3,
            )
            self.memory.add_event(
                episode.episode_id,
                {"kind": "execution", "actions": simulation.executed, "failed_step": simulation.failed_step},
                metadata={"kind": "execution", "reusable": False},
                importance=0.5,
            )
        self.memory.close_episode(episode.episode_id)
        if simulation is not None and simulation.success:
            added = set(simulation.final_state) - set(initial)
            removed = set(initial) - set(simulation.final_state)
            self.memory.episodes[episode.episode_id].context.update({"delta_added": tuple(sorted(added)), "delta_removed": tuple(sorted(removed))})
            self.episode_requirements[episode.episode_id] = initial
            for effect in added:
                self.effect_index.setdefault(effect, set()).add(episode.episode_id)
                self.effect_validity[(episode.episode_id, effect)] = True
            for removed_effect in removed:
                for prior_id in self.effect_index.get(removed_effect, set()):
                    prior_requirements = self.episode_requirements.get(prior_id, frozenset())
                    if self._contexts_overlap(prior_requirements, initial):
                        self.effect_validity[(prior_id, removed_effect)] = False
        return episode.episode_id

    def size(self) -> int:
        return len(self.memory.episodes)
