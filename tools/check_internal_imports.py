from pathlib import Path
import ast

root = Path('/home/ubuntu/grandnexus_rebuild/src')
package = root / 'grandnexus'
existing = {str(p.relative_to(root)).replace('/', '.')[:-3] for p in package.rglob('*.py') if p.name != '__init__.py'}
existing |= {str(p.relative_to(root)).replace('/', '.')[:-12] for p in package.rglob('__init__.py')}
missing = []
for path in package.rglob('*.py'):
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except SyntaxError as exc:
        print(f'SYNTAX {path}: {exc}')
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.startswith('grandnexus.'):
            mod = node.module
            if mod not in existing:
                missing.append((str(path.relative_to(root)), mod, node.lineno))
for item in sorted(set(missing)):
    print(f'{item[0]}:{item[2]} -> {item[1]}')
print(f'missing_internal_imports={len(set(missing))}')
