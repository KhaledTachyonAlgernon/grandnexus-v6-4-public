from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from collections import defaultdict, deque
import math
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

class AbstractionLevel(Enum):
    """Represents different levels of abstraction for concepts."""
    CONCRETE = 1      # Very specific instances or entities
    SPECIFIC = 2      # Specific types/categories
    GENERAL = 3       # General categories
    ABSTRACT = 4      # Abstract concepts
    UNIVERSAL = 5     # Universal principles or concepts


class RelationType(str, Enum):
    """Standard relation types with predefined semantics."""
    IS_A = "is_a"                 # Inheritance/subsumption (e.g., "dog is_a animal")
    PART_OF = "part_of"           # Composition (e.g., "wheel part_of car")
    HAS_PROPERTY = "has_property" # Attributes (e.g., "apple has_property red")
    RELATED_TO = "related_to"     # Generic association
    CAUSES = "causes"             # Causal relationship
    PRECEDED_BY = "preceded_by"   # Temporal precedence
    FOLLOWED_BY = "followed_by"   # Temporal succession
    SIMILAR_TO = "similar_to"     # Similarity or analogy
    OPPOSITE_OF = "opposite_of"   # Opposition or antonymy
    INSTANCE_OF = "instance_of"   # Instance relationship (e.g., "Fido instance_of dog")
    DEFINED_AS = "defined_as"     # Definition relationship


@dataclass
class Concept:
    """
    Represents a concept in the semantic memory with enhanced BioNeMo-inspired features.

    Attributes:
        concept_id (str): Unique identifier.
        name (str): Human-readable name (e.g., "Dog").
        description (str): Optional textual description.
        properties (Dict[str, Any]): Arbitrary attributes or key-value pairs.
        embedding (Optional[np.ndarray]): Vector representation for similarity calculations.
        synonyms (Set[str]): Alternate names or labels for the concept.
        importance (float): A measure of how relevant or "important" this concept is (0..1).
        abstraction_level (AbstractionLevel): The level of abstraction of this concept.
        activation (float): Current activation level (for spreading activation).
        last_accessed (float): Timestamp of last access (for recency effects).
        access_count (int): Number of times this concept has been accessed.
        confidence (float): Confidence in the concept's validity (0..1).
        source (str): Source of the concept (e.g., "user", "llm", "reasoning").
    """
    concept_id: str
    name: str
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    synonyms: Set[str] = field(default_factory=set)
    importance: float = 0.5
    abstraction_level: AbstractionLevel = AbstractionLevel.SPECIFIC
    activation: float = 0.0
    last_accessed: float = field(default_factory=lambda: 0.0)
    access_count: int = 0
    confidence: float = 1.0
    source: str = "user"

    def __repr__(self):
        return (f"<Concept id={self.concept_id}, "
                f"name={self.name}, level={self.abstraction_level.name}, "
                f"importance={self.importance:.2f}, activation={self.activation:.2f}>")


@dataclass
class Relation:
    """
    Represents a relationship between two concepts with enhanced features.

    Attributes:
        relation_id (str): Unique identifier for this relation.
        source_concept_id (str): ID of the source concept.
        relation_type (str): Type/category of the relationship.
        target_concept_id (str): ID of the target concept.
        weight (float): Strength/confidence of the relationship (0..1).
        properties (Dict[str, Any]): Additional info about the relation.
        bidirectional (bool): Whether the relation works in both directions.
        transitive (bool): Whether the relation is transitive.
        temporal (bool): Whether the relation has temporal significance.
        created_at (float): Timestamp when relation was created.
        confidence (float): Confidence in this relation's validity (0..1).
        source (str): Source of this relation (e.g., "user", "inference").
    """
    relation_id: str
    source_concept_id: str
    relation_type: Union[RelationType, str]
    target_concept_id: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    bidirectional: bool = False
    transitive: bool = False
    temporal: bool = False
    created_at: float = field(default_factory=lambda: 0.0)
    confidence: float = 1.0
    source: str = "user"

    def __post_init__(self):
        """Automatically set typical properties for standard relation types."""
        if isinstance(self.relation_type, str) and not isinstance(self.relation_type, RelationType):
            # Try to convert string to RelationType if possible
            try:
                self.relation_type = RelationType(self.relation_type)
            except ValueError:
                # Keep as string if not a standard type
                pass

        # Set defaults for standard relation types
        if isinstance(self.relation_type, RelationType):
            if self.relation_type == RelationType.IS_A:
                self.transitive = True
            elif self.relation_type == RelationType.PART_OF:
                self.transitive = True
            elif self.relation_type == RelationType.SIMILAR_TO:
                self.bidirectional = True
            elif self.relation_type == RelationType.OPPOSITE_OF:
                self.bidirectional = True
            elif self.relation_type == RelationType.PRECEDED_BY or self.relation_type == RelationType.FOLLOWED_BY:
                self.temporal = True

    def __repr__(self):
        return (f"<Relation id={self.relation_id}, "
                f"{self.source_concept_id} -{self.relation_type}-> "
                f"{self.target_concept_id}, weight={self.weight:.2f}, confidence={self.confidence:.2f}>")


@dataclass
class SemanticQuery:
    """
    Enhanced query container for specifying parameters when searching for concepts.

    Attributes:
        text (Optional[str]): A text string to match against a concept's name or synonyms.
        embedding (Optional[np.ndarray]): If set, we do an embedding-based similarity search.
        similarity_metric (str): 'cosine' or 'euclidean'.
        importance_threshold (float): Minimum concept importance required.
        max_results (int): Limit on returned concepts.
        relationship_filters (Optional[List[Tuple[str, str]]]):
            A list of (relation_type, concept_id). The concept must have a relationship of
            that type to the specified concept_id.
        synonyms_match (bool): If True, we also match `text` against synonyms.
        abstraction_levels (Optional[List[AbstractionLevel]]): Filter by abstraction levels.
        min_confidence (float): Minimum confidence level for retrieved concepts.
        context_boost (Dict[str, float]): Boost certain concept types or properties.
        recency_bias (float): Weight to give to recently accessed concepts (0-1).
        activation_threshold (float): Only return concepts with activation above this.
        include_inferred (bool): Whether to include inferred relationships.
        sort_by (str): How to sort results ('relevance', 'importance', 'confidence', etc.)
    """
    text: Optional[str] = None
    embedding: Optional[np.ndarray] = None
    similarity_metric: str = "cosine"
    importance_threshold: float = 0.0
    max_results: int = 20
    relationship_filters: Optional[List[Tuple[Union[RelationType, str], str]]] = None
    synonyms_match: bool = True
    abstraction_levels: Optional[List[AbstractionLevel]] = None
    min_confidence: float = 0.0
    context_boost: Dict[str, float] = field(default_factory=dict)
    recency_bias: float = 0.2
    activation_threshold: float = 0.0
    include_inferred: bool = True
    sort_by: str = "relevance"


class SemanticMemoryConfig:
    """
    Enhanced configuration for SemanticMemory.

    Attributes:
        embedding_function (Optional[Callable[[str], np.ndarray]]):
            A function that takes a string (name + synonyms) and returns an np.ndarray embedding.
        auto_link_graph (bool): If True, we call _sync_to_graph_subsystem whenever a concept changes.
        recency_decay (float): For advanced scoring if we track recency.
        max_concepts (int): If > 0, we limit the number of concepts and prune if exceeded.
        prune_policy (str): E.g. 'lowest_importance', 'oldest', or 'lowest_score'.
        activation_decay (float): Rate at which activation decays over time.
        activation_spread_factor (float): How much activation spreads to neighbors.
        relation_confidence_threshold (float): Minimum confidence for relations to be used in inference.
        inference_depth_limit (int): Maximum depth for transitive inference.
        enable_spreading_activation (bool): Whether to use spreading activation for search.
        max_activation_spreading_steps (int): Maximum steps for spreading activation.
        ontology_validation (bool): Validate ontological consistency when adding relations.
        default_concept_confidence (float): Default confidence for new concepts if not specified.
        context_window_size (int): Number of recent concepts to maintain in context window.
        similarity_threshold (float): Threshold for considering two embeddings similar.
        use_memory_consolidation (bool): Whether to periodically consolidate memory.
        consolidation_interval (int): How many operations before consolidation.
    """
    def __init__(self,
                 embedding_function: Optional[Callable[[str], np.ndarray]] = None,
                 auto_link_graph: bool = False,
                 recency_decay: float = 0.01,
                 max_concepts: int = 0,
                 prune_policy: str = "lowest_importance",
                 activation_decay: float = 0.05,
                 activation_spread_factor: float = 0.5,
                 relation_confidence_threshold: float = 0.5,
                 inference_depth_limit: int = 5,
                 enable_spreading_activation: bool = True,
                 max_activation_spreading_steps: int = 3,
                 ontology_validation: bool = True,
                 default_concept_confidence: float = 0.8,
                 context_window_size: int = 50,
                 similarity_threshold: float = 0.75,
                 use_memory_consolidation: bool = True,
                 consolidation_interval: int = 100):
        self.embedding_function = embedding_function
        self.auto_link_graph = auto_link_graph
        self.recency_decay = recency_decay
        self.max_concepts = max_concepts
        self.prune_policy = prune_policy
        self.activation_decay = activation_decay
        self.activation_spread_factor = activation_spread_factor
        self.relation_confidence_threshold = relation_confidence_threshold
        self.inference_depth_limit = inference_depth_limit
        self.enable_spreading_activation = enable_spreading_activation
        self.max_activation_spreading_steps = max_activation_spreading_steps
        self.ontology_validation = ontology_validation
        self.default_concept_confidence = default_concept_confidence
        self.context_window_size = context_window_size
        self.similarity_threshold = similarity_threshold
        self.use_memory_consolidation = use_memory_consolidation
        self.consolidation_interval = consolidation_interval


class SemanticMemory:
    MODULE_NAME = "semantic_memory"
    MSG_QUERY = "semantic_query"
    MSG_UPSERT = "semantic_upsert"

    def __init__(self, nexus_core: NexusCore, cfg: Optional[SemMemConfig] = None):
        self.logger = logging.getLogger("GrandNexus.Memory.SemanticMemory")
        self.nexus = nexus_core
        self.cfg = cfg or SemMemConfig()

        # Embedding model (thread-safe)
        self._model = SentenceTransformer(self.cfg.embed_model)

        # Vector store
        self._pg_conn: Optional["psycopg2.extensions.connection"] = None
        self._ann: Optional["AnnoyIndex"] = None
        self._ann_map: Dict[int, str] = {}

        # Graph store
        self._neo4j = None

        # Runtime
        self._lock = threading.RLock()
        self._running = False
        self._last_consolidate = 0.0
        self._pending_ann: List[Tuple[str, np.ndarray]] = []  # chunk_id, emb
        self._instance_id = str(uuid.uuid4())[:8]

        # Stats
        self._q_latency: List[float] = []
        self._upserts = 0

    # ─────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────
    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            self._running = True

        self._init_pgvector()
        self._init_neo4j()
        self._init_annoy()

        # Enregistrement NexusCore
        self.nexus.register_module(
            name=self.MODULE_NAME,
            module=self,
            dependencies=["cognitive_clock"],
        )

        # Tick subscription pour consolidation ANN ↔ PG
        clk = self.nexus.get_module("cognitive_clock")
        if clk:
            clk.subscribe(self.cfg.tick_channel, self._on_tick)

        self.logger.info(f"SemanticMemory {self._instance_id} started")
        return True

    def stop(self) -> bool:
        self._running = False
        if self._pg_conn:
            self._pg_conn.close()
        if self._neo4j:
            self._neo4j.close()
        return True

    # ─────────────────────────────────────────────────────────────────────
    # Backend initialisation
    # ─────────────────────────────────────────────────────────────────────
    def _init_pgvector(self):
        if not self.cfg.pg:
            return
        try:
            self._pg_conn = psycopg2.connect(self.cfg.pg.dsn)
            register_vector(self._pg_conn)
            cur = self._pg_conn.cursor()
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.cfg.pg.table} (
                    id TEXT PRIMARY KEY,
                    embedding VECTOR({self.cfg.pg.dim}),
                    metadata JSONB
                );
                """
            )
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_vec ON {self.cfg.pg.table} USING ivfflat (embedding vector_{self.cfg.pg.metric});")
            self._pg_conn.commit()
        except Exception as exc:
            self.logger.error(f"PGVector init failed: {exc}")
            self._pg_conn = None

    def _init_annoy(self):
        if not AnnoyCfg:
            return
        self._ann = AnnoyIndex(self.cfg.annoy.dim, self.cfg.annoy.metric)
        # will rebuild periodically

    def _init_neo4j(self):
        if not self.cfg.neo4j:
            return
        try:
            self._neo4j = GraphDatabase.driver(
                self.cfg.neo4j.uri, auth=(self.cfg.neo4j.user, self.cfg.neo4j.password)
            )
            with self._neo4j.session() as sess:
                sess.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Knowledge) REQUIRE n.id IS UNIQUE")
        except Exception as exc:
            self.logger.error(f"Neo4j init failed: {exc}")
            self._neo4j = None

    # ─────────────────────────────────────────────────────────────────────
    # Public API – upsert & query
    # ─────────────────────────────────────────────────────────────────────
    def upsert_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        triplets: Optional[List[Tuple[str, str, str]]] = None,
    ) -> str:
        doc_id = str(uuid.uuid4())[:8]
        emb = self._model.encode(text)
        meta = metadata or {}

        # Safety guard pre-check
        if self.cfg.safety_guard:
            sg = self.nexus.get_module(self.cfg.safety_guard)
            if sg and hasattr(sg, "is_allowed") and not sg.is_allowed(text, meta):
                self.logger.warning("SafetyGuard blocked upsert")
                return ""

        # PGVector
        if self._pg_conn:
            try:
                cur = self._pg_conn.cursor()
                cur.execute(
                    f"INSERT INTO {self.cfg.pg.table} (id, embedding, metadata) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                    (doc_id, emb.tolist(), json.dumps(meta)),
                )
                self._pg_conn.commit()
            except Exception as exc:
                self.logger.error(f"PG upsert error: {exc}")

        # Annoy (lazy)
        if self._ann is not None:
            self._pending_ann.append((doc_id, emb))

        # Neo4j triplets
        if triplets and self._neo4j:
            with self._neo4j.session() as s:
                for (sub, pred, obj) in triplets:
                    s.run(
                        """
                        MERGE (s:Entity {name:$sub})
                        MERGE (o:Entity {name:$obj})
                        MERGE (s)-[:REL {type:$pred, doc_id:$doc}]->(o)
                        """,
                        sub=sub, obj=obj, pred=pred, doc=doc_id,
                    )
                s.run("MERGE (d:Knowledge {id:$id}) SET d.text=$txt", id=doc_id, txt=text)

        with self._lock:
            self._upserts += 1
        return doc_id

    def semantic_query(
        self,
        text: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        start = time.perf_counter()
        emb = self._model.encode(text)

        results: List[Tuple[float, str, Dict[str, Any]]] = []

        # PGVector search
        if self._pg_conn:
            cur = self._pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(
                f"""
                SELECT id, metadata, 1 - (embedding <=> %s) AS score
                FROM {self.cfg.pg.table}
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (emb.tolist(), emb.tolist(), top_k * 2),
            )
            for row in cur.fetchall():
                results.append((row["score"], row["id"], dict(row["metadata"])))

        # Annoy fallback
        elif self._ann and self._ann.get_n_items():
            idxs, dists = self._ann.get_nns_by_vector(emb, top_k * 2, include_distances=True)
            for dist, idx in zip(dists, idxs):
                cid = self._ann_map.get(idx)
                results.append((1 - dist, cid, {}))

        # Sort & truncate
        results.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, cid, meta in results[: top_k]:
            trip = self._fetch_triplets(cid)
            out.append(
                {"doc_id": cid, "score": round(float(score), 3), "metadata": meta, "triplets": trip}
            )

        self._q_latency.append(time.perf_counter() - start)
        return out

    # ─────────────────────────────────────────────────────────────────────
    # Triplet fetch helper
    # ─────────────────────────────────────────────────────────────────────
    def _fetch_triplets(self, doc_id: str) -> List[Tuple[str, str, str]]:
        if not self._neo4j:
            return []
        with self._neo4j.session() as s:
            res = s.run(
                """
                MATCH (s:Entity)-[r:REL {doc_id:$doc}]->(o:Entity)
                RETURN s.name AS sub, r.type AS pred, o.name AS obj
                """,
                doc=doc_id,
            )
            return [(r["sub"], r["pred"], r["obj"]) for r in res]

    # ─────────────────────────────────────────────────────────────────────
    # Message interface
    # ─────────────────────────────────────────────────────────────────────
    def handle_message(self, msg: Dict[str, Any]) -> None:
        mtype = msg.get("type")
        if mtype == self.MSG_UPSERT:
            self.upsert_document(**msg["content"])
        elif mtype == self.MSG_QUERY:
            res = self.semantic_query(**msg["content"])
            # Répondre à la source si demandé
            if "reply_to" in msg:
                self.nexus.send_message(
                    source=self.MODULE_NAME,
                    target=msg["reply_to"],
                    message_type="semantic_response",
                    content=res,
                )

    # ─────────────────────────────────────────────────────────────────────
    # Tick consolidation (annoy build)
    # ─────────────────────────────────────────────────────────────────────
    def _on_tick(self, _):
        now = time.time()
        if self._ann is None or not self._pending_ann:
            return
        if now - self._last_consolidate < self.cfg.consolidate_every:
            return

        with self._lock:
            pending = list(self._pending_ann)
            self._pending_ann.clear()

        for cid, emb in pending:
            idx = self._ann.get_n_items()
            self._ann.add_item(idx, emb)
            self._ann_map[idx] = cid
        self._ann.build(self.cfg.annoy.n_trees)
        self._last_consolidate = now
        self.logger.info(f"Annoy index rebuilt with {self._ann.get_n_items()} items")

    # ─────────────────────────────────────────────────────────────────────
    # Health / status
    # ─────────────────────────────────────────────────────────────────────
    def health_check(self) -> Dict[str, Any]:
        lat = sum(self._q_latency) / len(self._q_latency) if self._q_latency else 0.0
        healthy = (self._pg_conn or self._ann) and (self._neo4j is not None)
        return {
            "latency_avg_ms": round(lat * 1_000, 2),
            "upserts": self._upserts,
            "vector_backend": "pgvector" if self._pg_conn else ("annoy" if self._ann else "none"),
            "graph_backend": bool(self._neo4j),
            "healthy": healthy,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "items_vector": self._ann.get_n_items() if self._ann else "N/A",
            "upserts": self._upserts,
        }


