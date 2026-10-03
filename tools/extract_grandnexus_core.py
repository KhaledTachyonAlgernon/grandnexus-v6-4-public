from pathlib import Path

src = Path('/home/ubuntu/upload/grandnexusv_6_4_15_05_2025.py')
out = Path('/home/ubuntu/grandnexus_core_candidate.py')
lines = src.read_text(encoding='utf-8', errors='replace').splitlines(True)
# Keep the principal GrandNexus implementation; the initial tree and the
# explainability/kernelbridge projects after line 64394 are separate artifacts.
kept = lines[67:64394]
# Remove raw curl/JavaScript client examples pasted between Python modules.
raw_prefixes = ('curl -N ', '-X POST ', 'http://localhost:8089/chat', 'const ev=', 'body:JSON.stringify', 'ev.onmessage=', '});')
kept = [line for line in kept if not line.lstrip().startswith(raw_prefixes)]
# A notebook concatenation left repeated future imports between modules;
# keep one legal copy at the beginning of the unified candidate.
future_lines = [line for line in kept if line.strip() == 'from __future__ import annotations']
kept = [line for line in kept if line.strip() != 'from __future__ import annotations']
if future_lines:
    kept.insert(0, future_lines[0])
# Correct the confirmed three-space method declaration.
for i, line in enumerate(kept):
    if line.startswith('   def _filter_by_selective_attention('):
        kept[i] = '    ' + line[3:]
# Correct the autonomous anomaly-filter function that retained class indentation.
    if line.startswith('    def create_anomaly_filter('):
        kept[i] = line[4:]
# The analogical-reasoning body is uniformly shifted by one indentation level.
inside_analogical_block = False
for i, line in enumerate(kept):
    if '# If we have attributes for entities, use them for mapping' in line:
        inside_analogical_block = True
    if inside_analogical_block and line.startswith('    '):
        kept[i] = line[4:]
    if '# Use LLM for more sophisticated analogical reasoning if available' in line:
        inside_analogical_block = False
out.write_text(''.join(kept), encoding='utf-8')
print(out)
print(f'lines={len(kept)}')
