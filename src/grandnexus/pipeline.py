"""Lightweight deterministic cognitive pipeline for GrandNexus MVP."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import time
import uuid

from .core.nexus_core import NexusCore
from .memory.working import WorkingMemoryItem
from .memory.episodic import EpisodeEvent, Episode
from .memory.semantic import Concept, Relation
from .cognition.perception.perception_core import InputType, PerceptionResult
from .cognition.reasoning.reasoning_core import ReasoningQuery, ReasoningResult
from .mvp_store import MvpStore
from .advanced_reasoning import AdvancedReasoner
from .memory_index import ExplainableMemoryIndex
from .symbolic_reasoner import Fact, SymbolicOutcome, SymbolicReasoner
from .metacognition_loop import MetacognitionLoop
from .hardware_contracts import PerceptionEvent


@dataclass
class PipelineResult:
    task_id: str
    perception: PerceptionResult
    working_item: WorkingMemoryItem
    episode: Episode
    concept: Concept
    relation: Relation
    reasoning: ReasoningResult
    trace: list[Dict[str, Any]] = field(default_factory=list)
    symbolic: SymbolicOutcome | None = None
    prediction_id: str | None = None


class LightCognitivePipeline:
    """A local, deterministic pipeline used as the first GrandNexus contract."""

    def __init__(self, core: NexusCore, store: MvpStore | None = None, advanced_reasoner: AdvancedReasoner | None = None, memory_index: ExplainableMemoryIndex | None = None, symbolic_reasoner: SymbolicReasoner | None = None, metacognition: MetacognitionLoop | None = None):
        self.core = core
        self.store = store
        self.advanced_reasoner = advanced_reasoner
        self.memory_index = memory_index
        self.symbolic_reasoner = symbolic_reasoner
        self.metacognition = metacognition

    def ingest_perception_event(self, event: PerceptionEvent) -> str:
        """Store a normalized sensory event without interpreting it as fact."""
        if self.memory_index is None:
            raise RuntimeError('memory_index is required for event ingestion')
        memory_id = f'event:{event.event_id}'
        payload = str(event.payload)
        self.memory_index.add(memory_id, payload, kind=f'perception:{event.modality}')
        return memory_id

    def process(self, text: str, source: str = "user") -> PipelineResult:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be a non-empty string")
        started = time.time()
        task_id = str(uuid.uuid4())
        trace: list[Dict[str, Any]] = []

        perception = PerceptionResult(input_type=InputType.TEXT, parsed_data=text.strip())
        trace.append({"stage": "perception", "type": perception.input_type.name})

        working_item = WorkingMemoryItem(item_id=str(uuid.uuid4()), content=text.strip(), source=source)
        trace.append({"stage": "working_memory", "item_id": working_item.item_id})

        event = EpisodeEvent(content=text.strip(), metadata={"source": source})
        episode = Episode(episode_id=str(uuid.uuid4()), events=[event], summary=text.strip())
        trace.append({"stage": "episodic_memory", "episode_id": episode.episode_id})

        concept = Concept(concept_id=str(uuid.uuid4()), name=text.strip(), source=source)
        relation = Relation(
            relation_id=str(uuid.uuid4()),
            source_concept_id=concept.concept_id,
            relation_type="related_to",
            target_concept_id=concept.concept_id,
            source="mvp",
        )
        trace.append({"stage": "semantic_memory", "concept_id": concept.concept_id})
        if self.memory_index is not None:
            self.memory_index.add(episode.episode_id, text.strip(), kind="episode")
            trace.append({"stage": "memory_index", "indexed": True})

        query = ReasoningQuery(question=text.strip(), context={"source": source})
        conclusions = [{"statement": f"Input received: {text.strip()}", "confidence": 1.0}]
        confidence = 1.0
        engine = "deterministic"
        if self.advanced_reasoner is not None:
            advanced = self.advanced_reasoner.reason(text.strip())
            conclusions.append({"statement": advanced.statement, "confidence": advanced.confidence})
            confidence = advanced.confidence
            engine = advanced.engine
        reasoning = ReasoningResult(
            query_id=query.query_id,
            conclusions=conclusions,
            confidence=confidence,
            complete=True,
            processing_time=time.time() - started,
        )
        trace.append({"stage": "reasoning", "query_id": query.query_id, "complete": True, "engine": engine})

        symbolic = None
        if self.symbolic_reasoner is not None:
            symbolic = self.symbolic_reasoner.prove(Fact.parse(text.strip()))
            trace.append({"stage": "symbolic_reasoning", "status": symbolic.status})
        prediction_id = None
        if self.metacognition is not None:
            prediction_id = self.metacognition.register(confidence, {"task_id": task_id, "query": text.strip()})
            trace.append({"stage": "metacognition", "prediction_id": prediction_id, "confidence": confidence})
        result = PipelineResult(task_id=task_id, perception=perception, working_item=working_item, episode=episode, concept=concept, relation=relation, reasoning=reasoning, trace=trace, symbolic=symbolic, prediction_id=prediction_id)
        if self.store is not None:
            self.store.save_result(result)
        return result
