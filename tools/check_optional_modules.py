from pathlib import Path
import ast
import importlib.util

root = Path('/home/ubuntu/grandnexus_rebuild/src')
for path in sorted((root / 'grandnexus').rglob('*.py')):
    if path.name == '__init__.py' or path.name == '_legacy_core.py':
        continue
    rel = path.relative_to(root).with_suffix('')
    mod = '.'.join(rel.parts)
    try:
        ast.parse(path.read_text(encoding='utf-8'))
    except SyntaxError as exc:
        print(f'{mod}\tSYNTAX\t{exc}')
        continue
    try:
        spec = importlib.util.find_spec(mod)
        if spec is None:
            print(f'{mod}\tNO_SPEC')
        else:
            print(f'{mod}\tSPEC_OK')
    except Exception as exc:
        print(f'{mod}\tSPEC_ERROR\t{type(exc).__name__}: {exc}')
