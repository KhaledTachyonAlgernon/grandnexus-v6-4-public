"""Conflict policy: flexible priorities inside a safe envelope, hard safety gates outside it."""
from __future__ import annotations

from dataclasses import dataclass

from .drive_module import DriveModule, DriveSignal


@dataclass(frozen=True)
class DriveResolution:
    status: str
    selected_drive: str | None
    reason: str
    ranked: tuple[tuple[str, float], ...]


class DrivePolicy:
    def __init__(self, drives: DriveModule):
        self.drives = drives

    def resolve(self, signals: list[DriveSignal], *, external_effect: bool = False, risk: str = 'low', reversible: bool = True, contradiction: bool = False, simulation_only: bool = True) -> DriveResolution:
        ranked = tuple((signal.drive, round(priority, 6)) for signal, priority in self.drives.ranked(signals))
        if external_effect:
            return DriveResolution('approval_required', None, 'external effects require explicit hardware policy', ranked)
        if contradiction:
            return DriveResolution('verification_first', 'safety_check', 'contradiction must be resolved before progress', ranked)
        if risk not in {'low', 'medium', 'high'}:
            raise ValueError('risk must be low, medium or high')
        if risk == 'high':
            if simulation_only:
                return DriveResolution('simulation_allowed_with_review', ranked[0][0] if ranked else None, 'high-risk reasoning is allowed only inside simulation with review', ranked)
            return DriveResolution('refused', None, 'high risk exceeds execution policy', ranked)
        if not reversible and risk != 'low':
            return DriveResolution('verification_first', 'safety_check', 'non-reversible medium-risk objective requires verification', ranked)
        if not ranked:
            return DriveResolution('no_drive', None, 'no enabled drive signal', ranked)
        return DriveResolution('progress_allowed', ranked[0][0], 'selected highest-priority drive within safe envelope', ranked)
