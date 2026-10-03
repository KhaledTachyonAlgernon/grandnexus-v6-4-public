"""Explicit activation registry for future GrandNexus branches."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BranchProfile:
    name: str
    layer: str
    dependencies: tuple[str, ...] = ()
    simulation_first: bool = True
    enabled: bool = False


BRANCH_PROFILES = {
    'vision_mvp': BranchProfile('vision_mvp', 'primordial', (), True, False),
    'audio_mvp': BranchProfile('audio_mvp', 'primordial', (), True, False),
    'semantic_embeddings': BranchProfile('semantic_embeddings', 'orion', ('sentence_transformers',), True, False),
    'local_llm': BranchProfile('local_llm', 'orion', ('torch', 'transformers'), True, False),
    'planning': BranchProfile('planning', 'orion', (), True, False),
    'multi_agent': BranchProfile('multi_agent', 'orion', (), True, False),
    'knowledge_graph': BranchProfile('knowledge_graph', 'orion', ('neo4j',), True, False),
    'robotics_mvp': BranchProfile('robotics_mvp', 'primordial', (), True, False),
    'reinforcement_sim': BranchProfile('reinforcement_sim', 'pleiade', ('gymnasium',), True, False),
    'nexus_federation': BranchProfile('nexus_federation', 'pleiade', (), True, False),
}


def activation_order() -> list[str]:
    return ['vision_mvp', 'audio_mvp', 'semantic_embeddings', 'planning', 'local_llm', 'multi_agent', 'knowledge_graph', 'robotics_mvp', 'reinforcement_sim', 'nexus_federation']
