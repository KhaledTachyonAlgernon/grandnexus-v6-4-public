from __future__ import annotations
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import logging
import threading
import time
import uuid
import sqlite3
import json  # For serializing/deserializing module configurations
from typing import Dict, Any, Optional, List, Callable, Union, Tuple, Set  # Importer Set
import heapq  # Correctly manage priorities



from .memory_manager import MemoryItem

@dataclass
class WorkingMemoryItem:
    """
    Represents a single item stored in working memory.

    Attributes:
        item_id (str): Unique identifier.
        content (Any): Actual data (text, partial results, etc.).
        source (str): Which module or process inserted it.
        timestamp (float): Creation or last update time.
        importance (float): Salience or relevance (0..1).
        metadata (Dict[str, Any]): Additional info.
        expiration_time (Optional[float]): If set, we consider the item expired after that time.
        embedding (Optional[np.ndarray]): If config provides an embedding_function, we store the computed vector here.
    """
    item_id: str
    content: Any
    source: str
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    expiration_time: Optional[float] = None
    embedding: Optional[np.ndarray] = None

    def __repr__(self) -> str:
        return (f"<WorkingMemoryItem id={self.item_id[-8:]}, "
                f"source={self.source}, importance={self.importance:.2f}>")


@dataclass
class WorkingMemoryConfig:
    """
    Configuration for the WorkingMemory.

    Attributes:
        capacity (int): Max number of items allowed.
        eviction_policy (str): 'LRU', 'LFU', or 'priority'.
        default_importance (float): Default if importance not provided
        expiration_enabled (bool): If True, we consider item.expiration_time for removal
        default_expiration_time (Optional[float]): If set, used when adding items
        embedding_function (Optional[Callable[[Any], np.ndarray]]): For item embeddings
        recency_bias (float): Weighted factor for recency in retrieval scoring
        auto_transfer_callback (Optional[Callable[[WorkingMemoryItem], None]]):
            If set, we call it before eviction, allowing items to be "saved" elsewhere
    """
    def __init__(self,
                 capacity: int = 100,
                 eviction_policy: str = "LRU",
                 default_importance: float = 0.5,
                 expiration_enabled: bool = False,
                 default_expiration_time: Optional[float] = None,
                 embedding_function: Optional[Callable[[Any], np.ndarray]] = None,
                 recency_bias: float = 0.0,
                 auto_transfer_callback: Optional[Callable[[WorkingMemoryItem], None]] = None
                 ):
        self.capacity = capacity
        self.eviction_policy = eviction_policy
        self.default_importance = default_importance
        self.expiration_enabled = expiration_enabled
        self.default_expiration_time = default_expiration_time
        self.embedding_function = embedding_function
        self.recency_bias = recency_bias
        self.auto_transfer_callback = auto_transfer_callback


class WorkingMemory:
    MODULE_NAME = "working_memory"

    def __init__(
        self,
        nexus_core: NexusCore,
        config: Optional[WMConfig] = None,
    ):
        self.logger = logging.getLogger("GrandNexus.Memory.WorkingMemory")
        self.nexus_core = nexus_core
        self.config = config or WMConfig()

        # Storage
        self._lock = threading.RLock()
        self._store: Dict[str, MemoryChunk] = {}
        self._lru_order: Deque[str] = deque()

        # Stats
        self._hit = 0
        self._miss = 0

        # Drives
        self._drives: Dict[str, float] = {}

        # Runtime
        self._running = False
        self._instance_id = str(uuid.uuid4())[:8]

    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────
    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            self._running = True

        # Register
        self.nexus_core.register_module(
            name=self.MODULE_NAME,
            module=self,
            dependencies=["cognitive_clock", self.config.drive_source],
        )

        # Subscribe clock
        clock = self.nexus_core.get_module("cognitive_clock")
        if clock:
            clock.subscribe(self.config.tick_channel, self._on_tick)

        self.logger.info(f"WorkingMemory {self._instance_id} started")
        return True

    def stop(self) -> bool:
        with self._lock:
            self._running = False
        return True

    # ─────────────────────────────────────────────────────────────────────
    # Insertion
    # ─────────────────────────────────────────────────────────────────────
    def put(
        self,
        data: Any,
        salience: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None,
    ) -> str:
        if embedding is None and self.config.embedding_fn:
            try:
                embedding = self.config.embedding_fn(data)
            except Exception as exc:
                self.logger.warning(f"Embedding failure: {exc}")

        chunk = MemoryChunk(
            chunk_id=str(uuid.uuid4())[:8],
            data=data,
            timestamp=time.time(),
            salience=salience,
            embedding=embedding,
            metadata=metadata or {},
        )

        with self._lock:
            # Eviction if necessary
            if len(self._store) >= self.config.capacity:
                self._evict_one()

            self._store[chunk.chunk_id] = chunk
            self._lru_order.append(chunk.chunk_id)
        return chunk.chunk_id

    # ─────────────────────────────────────────────────────────────────────
    # Retrieval
    # ─────────────────────────────────────────────────────────────────────
    def get(
        self,
        chunk_id: str,
    ) -> Optional[MemoryChunk]:
        with self._lock:
            chunk = self._store.get(chunk_id)
            if chunk:
                self._hit += 1
                chunk.access_count += 1
                chunk.timestamp = time.time()
                # move to end (most recent)
                try:
                    self._lru_order.remove(chunk_id)
                except ValueError:
                    pass
                self._lru_order.append(chunk_id)
            else:
                self._miss += 1
        return chunk

    def query(
        self,
        predicate: Optional[Callable[[MemoryChunk], bool]] = None,
        embedding: Optional[np.ndarray] = None,
        top_k: Optional[int] = None,
    ) -> List[MemoryChunk]:
        results: List[Tuple[float, MemoryChunk]] = []
        now = time.time()
        with self._lock:
            for ch in self._store.values():
                if predicate and not predicate(ch):
                    continue

                score = self._current_salience(ch, now)
                # embedding similarity boost
                if embedding is not None and ch.embedding is not None:
                    sim = self._cos_sim(embedding, ch.embedding)
                    score += sim
                results.append((score, ch))

        results.sort(key=lambda x: x[0], reverse=True)
        k = top_k or self.config.max_query_results
        out = [c for _, c in results[:k]]
        for c in out:
            self.get(c.chunk_id)   # update LRU + stats
        return out

    # ─────────────────────────────────────────────────────────────────────
    # Internal utilities
    # ─────────────────────────────────────────────────────────────────────
    def _evict_one(self) -> None:
        """LRU with salience fallback."""
        while self._lru_order:
            cid = self._lru_order.popleft()
            if cid in self._store:
                del self._store[cid]
                self.logger.debug(f"Evicted chunk {cid}")
                return

    def _current_salience(self, chunk: MemoryChunk, now: float) -> float:
        age = now - chunk.timestamp
        λ = math.log(2) / self.config.decay_half_life
        # Drive-modulated decay
        λ *= 1.0 + self._drives.get("FATIGUE", 0.0)
        return chunk.salience * math.exp(-λ * age)

    @staticmethod
    def _cos_sim(a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    # ─────────────────────────────────────────────────────────────────────
    # Tick & consolidation
    # ─────────────────────────────────────────────────────────────────────
    def _on_tick(self, payload: Dict[str, Any]) -> None:
        now = time.time()
        to_consolidate = []
        with self._lock:
            for cid in list(self._store.keys()):
                ch = self._store[cid]
                # Decay update & consolidation
                if (now - ch.timestamp) >= self.config.consolidation_age:
                    to_consolidate.append(ch)
                    del self._store[cid]
                    try:
                        self._lru_order.remove(cid)
                    except ValueError:
                        pass

        # Send to EpisodicMemory
        for ch in to_consolidate:
            self.nexus_core.send_message(
                source=self.MODULE_NAME,
                target=self.config.episodic_target,
                message_type="episodic_ingest",
                content={
                    "chunk_id": ch.chunk_id,
                    "data": ch.data,
                    "metadata": ch.metadata,
                    "embedding": ch.embedding.tolist() if ch.embedding is not None else None,
                    "timestamp": ch.timestamp,
                },
                priority=5,
            )

    # ─────────────────────────────────────────────────────────────────────
    # Drives update via message
    # ─────────────────────────────────────────────────────────────────────
    def handle_message(self, msg: Dict[str, Any]) -> None:
        if msg.get("type") == "homeostasis_drive":
            with self._lock:
                self._drives = msg["content"]

    # ─────────────────────────────────────────────────────────────────────
    # Health / status
    # ─────────────────────────────────────────────────────────────────────
    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            miss_ratio = self._miss / max(1, self._hit + self._miss)
            healthy = len(self._store) < self.config.capacity and miss_ratio < 0.5
            return {
                "items": len(self._store),
                "hit": self._hit,
                "miss": self._miss,
                "miss_ratio": round(miss_ratio, 3),
                "healthy": healthy,
            }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "items": len(self._store),
                "lru_len": len(self._lru_order),
                "drives": {k: round(v, 2) for k, v in self._drives.items()},
            }


