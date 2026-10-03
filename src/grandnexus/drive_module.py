"""Observable internal drives that propose, but never directly execute, goals."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import sqlite3
from pathlib import Path
import uuid
from typing import Any


@dataclass(frozen=True)
class Drive:
    name: str
    weight: float = 1.0
    enabled: bool = True


@dataclass(frozen=True)
class DriveSignal:
    drive: str
    intensity: float
    urgency: float = 0.0
    confidence: float = 0.0
    context: dict[str, Any] | None = None

    def priority(self, weight: float = 1.0) -> float:
        values = [max(0.0, min(1.0, value)) for value in (self.intensity, self.urgency, self.confidence)]
        return weight * (0.5 * values[0] + 0.3 * values[1] + 0.2 * (1.0 - values[2]))


@dataclass(frozen=True)
class GoalProposal:
    proposal_id: str
    drive: str
    goal: str
    priority: float
    status: str = 'pending'
    reason: str = ''


class DriveModule:
    def __init__(self, db_file: str | Path):
        self.db_file = str(db_file)
        self.drives: dict[str, Drive] = {}
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS drive_proposals (proposal_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

    def register_drive(self, name: str, weight: float = 1.0, enabled: bool = True) -> Drive:
        if not name.strip() or weight < 0:
            raise ValueError('drive name must be non-empty and weight must be non-negative')
        drive = Drive(name.strip(), weight, enabled)
        self.drives[drive.name] = drive
        return drive

    def propose(self, signal: DriveSignal, goal: str) -> GoalProposal:
        if not 0.0 <= signal.intensity <= 1.0 or not 0.0 <= signal.urgency <= 1.0 or not 0.0 <= signal.confidence <= 1.0:
            raise ValueError('drive signal values must be between 0 and 1')
        if not goal.strip():
            raise ValueError('goal must be non-empty')
        drive = self.drives.get(signal.drive, Drive(signal.drive))
        if not drive.enabled:
            raise ValueError('drive is disabled')
        priority = round(signal.priority(drive.weight), 6)
        proposal = GoalProposal(str(uuid.uuid4()), signal.drive, goal.strip(), priority, 'pending', 'goal requires planner and policy checks')
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT INTO drive_proposals VALUES (?, ?)', (proposal.proposal_id, json.dumps(asdict(proposal), ensure_ascii=False)))
        return proposal

    def ranked(self, signals: list[DriveSignal]) -> list[tuple[DriveSignal, float]]:
        ranked = [(signal, signal.priority(self.drives.get(signal.drive, Drive(signal.drive)).weight)) for signal in signals if self.drives.get(signal.drive, Drive(signal.drive)).enabled]
        return sorted(ranked, key=lambda item: item[1], reverse=True)
