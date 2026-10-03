from pathlib import Path
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.metacognition_loop import MetacognitionLoop

loop = MetacognitionLoop()
assert loop.review().recommendation == 'collect_more_outcomes'
first = loop.register(0.9, {'task': 'deduction'})
second = loop.register(0.8, {'task': 'recall'})
loop.observe(first, True)
loop.observe(second, False)
review = loop.review()
assert review.count == 2
assert review.accuracy == 0.5
assert math.isclose(review.mean_confidence, 0.85, rel_tol=1e-9)
assert math.isclose(review.calibration_gap, 0.35, rel_tol=1e-9)
assert review.recommendation == 'reduce_confidence_or_request_verification'
print('metacognition=OK')
