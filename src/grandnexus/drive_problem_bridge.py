"""Bridge from internal drive proposals to explicit ProblemSolver goals."""
from __future__ import annotations

from dataclasses import dataclass

from .drive_module import DriveModule, DriveSignal, GoalProposal


@dataclass(frozen=True)
class DriveDecision:
    proposal: GoalProposal | None
    status: str
    reason: str


class DriveProblemBridge:
    def __init__(self, drives: DriveModule):
        self.drives = drives

    def propose_highest(self, signals: list[DriveSignal], goals_by_drive: dict[str, str]) -> DriveDecision:
        ranked = self.drives.ranked(signals)
        if not ranked:
            return DriveDecision(None, 'no_drive', 'no enabled drive has a signal')
        signal, _priority = ranked[0]
        goal = goals_by_drive.get(signal.drive)
        if not goal:
            return DriveDecision(None, 'clarification_required', f'no goal mapping for drive {signal.drive}')
        proposal = self.drives.propose(signal, goal)
        return DriveDecision(proposal, 'pending', 'goal proposed for planner review')
