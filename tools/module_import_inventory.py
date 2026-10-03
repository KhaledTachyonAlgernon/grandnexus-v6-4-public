from pathlib import Path
import importlib.util
import json
import sys

root = Path(__file__).resolve().parents[1]
src = root / 'src'
sys.path.insert(0, str(src))
results = []
for path in sorted((src / 'grandnexus').rglob('*.py')):
    if path.name == '__init__.py':
        continue
    module = '.'.join(path.relative_to(src).with_suffix('').parts)
    spec = importlib.util.spec_from_file_location(module, path)
    record = {'module': module, 'file': str(path.relative_to(root))}
    try:
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
        record['syntax'] = 'ok'
    except Exception as exc:
        record['syntax'] = f'{type(exc).__name__}: {exc}'
    results.append(record)
print(json.dumps(results, ensure_ascii=False, indent=2))
