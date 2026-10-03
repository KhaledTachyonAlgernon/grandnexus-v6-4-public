from pathlib import Path
import tempfile
import time
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.core.nexus_core import NexusCore
from grandnexus.pipeline import LightCognitivePipeline

count = 200
with tempfile.TemporaryDirectory() as tmp:
    core = NexusCore(enable_async_messaging=False, db_file=str(Path(tmp) / 'nexus.db'))
    pipeline = LightCognitivePipeline(core)
    started = time.perf_counter()
    results = [pipeline.process(f'benchmark input {i}') for i in range(count)]
    elapsed = time.perf_counter() - started
assert len({r.task_id for r in results}) == count
print(f'iterations={count}')
print(f'elapsed_seconds={elapsed:.6f}')
print(f'items_per_second={count / elapsed:.2f}')
