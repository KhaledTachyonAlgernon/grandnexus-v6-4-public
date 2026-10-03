"""Safe hardware-independent robot action simulator."""
from __future__ import annotations

from .hardware_contracts import ActionRequest, ActionResult


class RobotSimulator:
    def __init__(self, max_position: float = 1.0):
        if max_position <= 0:
            raise ValueError('max_position must be positive')
        self.max_position = max_position
        self.state = {'position': 0.0, 'enabled': True}

    def execute(self, request: ActionRequest) -> ActionResult:
        if not request.simulation:
            return ActionResult(request.request_id, accepted=False, executed=False, simulation=False, message='real hardware disabled')
        if not self.state['enabled']:
            return ActionResult(request.request_id, accepted=False, executed=False, simulation=True, message='simulator stopped', state=dict(self.state))
        if request.action == 'move':
            target = float(request.parameters.get('position', 0.0))
            if not -self.max_position <= target <= self.max_position:
                return ActionResult(request.request_id, accepted=False, executed=False, simulation=True, message='position limit exceeded', state=dict(self.state))
            self.state['position'] = target
            return ActionResult(request.request_id, accepted=True, executed=True, simulation=True, message='simulated move executed', state=dict(self.state))
        if request.action == 'stop':
            self.stop()
            return ActionResult(request.request_id, accepted=True, executed=True, simulation=True, message='simulator stopped', state=dict(self.state))
        return ActionResult(request.request_id, accepted=False, executed=False, simulation=True, message='unknown action', state=dict(self.state))

    def stop(self) -> None:
        self.state['enabled'] = False
