from pathlib import Path

root = Path('/home/ubuntu/grandnexus_rebuild/src/grandnexus/cognition/perception')
for path in root.glob('*.py'):
    if path.name == '__init__.py':
        continue
    lines = path.read_text(encoding='utf-8').splitlines(True)
    cleaned = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped == 'from __future__ import annotations':
            continue
        if stripped.startswith('from grandnexus.'):
            skip = stripped.endswith('(')
            continue
        if skip:
            if ')' in line:
                skip = False
            continue
        cleaned.append(line)
    header = 'from __future__ import annotations\n'
    if path.name == 'perception_core.py':
        header += 'from grandnexus.cognition.cognition_manager import CognitionManager, CognitiveModuleBase, CognitiveProcessType, CognitiveMode, CognitiveContext, CognitiveRequest\n'
    path.write_text(header + ''.join(cleaned), encoding='utf-8')
    print(path)
