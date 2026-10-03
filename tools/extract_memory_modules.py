from pathlib import Path
import ast

root = Path('/home/ubuntu/grandnexus_rebuild')
source = (root / 'reference' / 'grandnexus_core_candidate.py').read_text(encoding='utf-8')
lines = source.splitlines(True)
tree = ast.parse(source)
classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
imports = ''.join(lines[:next(node.lineno for node in tree.body if isinstance(node, ast.ClassDef)) - 1])
groups = {
    'memory/memory_manager.py': ['MemoryItem', 'NexusMemoryManager'],
    'memory/episodic.py': ['MemoryStrength', 'EpisodeType', 'RetrievalMode', 'EpisodeEvent', 'Episode', 'Epoch', 'EpisodicQuery', 'EpisodicMemoryConfig', 'EpisodicMemoryState', 'EpisodicMemory'],
    'memory/semantic.py': ['AbstractionLevel', 'RelationType', 'Concept', 'Relation', 'SemanticQuery', 'SemanticMemoryConfig', 'SemanticMemory'],
    'memory/working.py': ['WorkingMemoryItem', 'WorkingMemoryConfig', 'WorkingMemory'],
}
for relpath, names in groups.items():
    selected = [classes[name] for name in names]
    selected.sort(key=lambda node: node.lineno)
    body = ''.join(''.join(lines[node.lineno - 1:node.end_lineno]) + '\n\n' for node in selected)
    extra = ''
    if relpath.endswith('episodic.py'):
        extra = 'from .memory_manager import MemoryItem\n'
    if relpath.endswith('semantic.py'):
        extra = 'from .memory_manager import MemoryItem\n'
    if relpath.endswith('working.py'):
        extra = 'from .memory_manager import MemoryItem\n'
    destination = root / 'src' / 'grandnexus' / relpath
    destination.write_text(imports + '\n' + extra + '\n' + body, encoding='utf-8')
    print(destination)
