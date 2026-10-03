from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.branch_profiles import BRANCH_PROFILES, activation_order

order = activation_order()
assert order.index('semantic_embeddings') < order.index('local_llm')
assert order.index('planning') < order.index('multi_agent')
assert BRANCH_PROFILES['robotics_mvp'].simulation_first
assert BRANCH_PROFILES['nexus_federation'].layer == 'pleiade'
assert all(not profile.enabled for profile in BRANCH_PROFILES.values())
print('branch_profiles=OK')
