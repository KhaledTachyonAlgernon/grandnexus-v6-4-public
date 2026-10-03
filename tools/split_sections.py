from pathlib import Path
import re
import json

root = Path('/home/ubuntu/grandnexus_rebuild')
source = root / 'reference' / 'grandnexus_core_candidate.py'
out_root = root / 'src' / 'grandnexus'
text = source.read_text(encoding='utf-8')
lines = text.splitlines(True)
marker = re.compile(r'^# grandnexus/(.+?)\s*$')
sections = []
for number, line in enumerate(lines):
    match = marker.match(line)
    if match:
        sections.append((number, match.group(1)))

# Keep the original unified candidate under a package-private compatibility name.
(out_root / '_legacy_core.py').write_text(text, encoding='utf-8')
for package in ('core', 'memory', 'cognition', 'perception', 'reasoning', 'learning', 'metacognition', 'clock', 'sensors', 'actuators', 'homeostasis', 'planning', 'security', 'ops', 'graph', 'io', 'multiagent', 'kernel', 'evolution', 'simulation', 'distributed'):
    directory = out_root / package
    directory.mkdir(parents=True, exist_ok=True)
    (directory / '__init__.py').touch()
(out_root / '__init__.py').write_text('"""GrandNexus v6.4 reconstructed package (incremental recovery)."""\n', encoding='utf-8')

manifest = []
for index, (start, relpath) in enumerate(sections):
    end = sections[index + 1][0] if index + 1 < len(sections) else len(lines)
    destination = out_root / relpath
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(''.join(lines[start:end]), encoding='utf-8')
    manifest.append({'source_line': start + 1, 'path': str(destination.relative_to(root)), 'lines': end - start})
(root / 'module_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'sections': len(sections), 'manifest': str(root / 'module_manifest.json')}, ensure_ascii=False))
