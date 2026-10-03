from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.memory_index import ExplainableMemoryIndex

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / 'memory.db'
    index = ExplainableMemoryIndex(db)
    index.add('m1', 'Le chat dort sur le tapis', kind='episode')
    index.add('m2', 'Le système mémorise une information', kind='semantic')
    index.add('m3', 'Une plante a besoin de lumière', kind='fact')
    hits = index.search('système mémorise information')
    assert hits and hits[0].memory_id == 'm2'
    assert hits[0].score == 1.0
    restored = ExplainableMemoryIndex(db)
    assert restored.count() == 3
    assert restored.search('plante lumière')[0].memory_id == 'm3'
print('memory_index=OK')
