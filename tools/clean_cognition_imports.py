from pathlib import Path

path = Path('/home/ubuntu/grandnexus_rebuild/src/grandnexus/cognition/cognition_manager.py')
lines = path.read_text(encoding='utf-8').splitlines(True)
clean = []
skip = False
for line in lines:
    stripped = line.strip()
    if stripped.startswith('from grandnexus.'):
        # Remove single-line and parenthesized internal imports from the
        # concatenated source; the orchestrator resolves modules lazily.
        skip = not stripped.endswith(')') and stripped.endswith('(')
        continue
    if skip:
        if ')' in line:
            skip = False
        continue
    clean.append(line)
path.write_text(''.join(clean), encoding='utf-8')
print(path)
