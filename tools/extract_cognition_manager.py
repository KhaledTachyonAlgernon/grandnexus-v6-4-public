from pathlib import Path
import ast

root = Path('/home/ubuntu/grandnexus_rebuild')
source = (root / 'reference' / 'grandnexus_core_candidate.py').read_text(encoding='utf-8')
lines = source.splitlines(True)
tree = ast.parse(source)
wanted = {'CognitiveEventType', 'CognitiveEvent', 'CognitiveTask', 'CognitiveState', 'CognitionManager'}
classes = []
seen = set()
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name in wanted and node.name not in seen:
        classes.append(node)
        seen.add(node.name)
classes.sort(key=lambda node: node.lineno)
first_class = min(node.lineno for node in classes)
imports = []
for node in tree.body:
    if getattr(node, 'lineno', first_class) >= first_class:
        break
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        imports.append(''.join(lines[node.lineno - 1:node.end_lineno]))
prefix = '\n'.join(imports) + '\n'
body = ''.join(''.join(lines[node.lineno - 1:node.end_lineno]) + '\n\n' for node in classes)
out = root / 'src' / 'grandnexus' / 'cognition' / 'cognition_manager.py'
out.write_text(prefix + '\n' + body, encoding='utf-8')
print(out)
print('classes=' + ','.join(node.name for node in classes))
