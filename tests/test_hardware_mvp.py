from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grandnexus.hardware_contracts import ActionRequest, PerceptionEvent
from grandnexus.robot_simulator import RobotSimulator
from grandnexus.sensory_adapters import RecordedAudioAdapter, RecordedVisionAdapter

vision = RecordedVisionAdapter().observe('/tmp/frame.png', 'un objet dans une scène', 0.8)
audio = RecordedAudioAdapter().transcribe('/tmp/sample.wav', 'bonjour GrandNexus', 0.9, 'fr')
assert vision.modality == 'vision' and vision.confidence == 0.8
assert audio.modality == 'audio' and audio.payload['language'] == 'fr'
robot = RobotSimulator(max_position=1.0)
move = robot.execute(ActionRequest('move', {'position': 0.5}))
assert move.accepted and move.executed and move.state['position'] == 0.5
rejected = robot.execute(ActionRequest('move', {'position': 2.0}))
assert not rejected.accepted and not rejected.executed
real = robot.execute(ActionRequest('move', {'position': 0.1}, simulation=False))
assert not real.accepted and real.message == 'real hardware disabled'
robot.stop()
stopped = robot.execute(ActionRequest('move', {'position': 0.1}))
assert not stopped.accepted and stopped.message == 'simulator stopped'
try:
    PerceptionEvent('vision', {}, 1.2, 'test')
except ValueError:
    pass
else:
    raise AssertionError('invalid confidence accepted')
print('hardware_mvp=OK')
