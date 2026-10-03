from pathlib import Path
import ast

root = Path('/home/ubuntu/grandnexus_rebuild')
source_path = root / 'reference' / 'grandnexus_core_candidate.py'
source = source_path.read_text(encoding='utf-8')
lines = source.splitlines(True)
tree = ast.parse(source)
classes = {'NexusCore', 'ErrorRecoveryManager', 'ErrorRecoveryExtension', 'ModuleRegistry'}
selected = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in classes]
selected.sort(key=lambda node: node.lineno)
# Preserve imports and definitions before the first class; they contain the
# standard-library support used by the core classes.
first_class_line = min(node.lineno for node in selected)
prefix = ''.join(lines[:first_class_line - 1])
body = ''.join(''.join(lines[node.lineno - 1:node.end_lineno]) + '\n\n' for node in selected)
out = root / 'src' / 'grandnexus' / 'core' / 'nexus_core.py'
out.write_text(prefix + '\n' + body, encoding='utf-8')
print(out)
print('classes=' + ','.join(node.name for node in selected))
