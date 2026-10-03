"""Metacognitive feedback for plan selection, without automatic preference changes."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from .branch_contracts import CognitivePlan
from .plan_evaluator import PlanSelection


@dataclass(frozen=True)
class PlanFeedback:
    feedback_id: str
    selected_request_id: str | None
    selected_cost: int | None
    selected_risk: str | None
    selected_confidence: float | None
    simulation_success: bool
    predicted_objectives: tuple[str, ...]
    observed_state: tuple[str, ...]
    alternative_count: int
    recommendation: str


class PlanFeedbackStore:
    def __init__(self, db_file: str | Path):
        self.db_file = str(db_file)
        with sqlite3.connect(self.db_file) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS plan_feedback (feedback_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def record(self, selection: PlanSelection, simulation_success: bool, observed_state: set[str] | frozenset[str] = (), objectives: tuple[str, ...] = ()) -> PlanFeedback:
        selected = selection.selected
        score = None
        if selected is not None:
            from .plan_evaluator import PlanEvaluator
            score = PlanEvaluator().score(selected)
        recommendation = 'collect_more_outcomes'
        if selection.status == 'clarification_required':
            recommendation = 'request_clarification'
        elif not simulation_success:
            recommendation = 'investigate_failed_simulation'
        elif score is not None:
            recommendation = 'candidate_preference_only_after_regression_check'
        feedback = PlanFeedback(str(uuid.uuid4()), selected.request_id if selected else None, score.cost if score else None, score.risk if score else None, selected.confidence if selected else None, simulation_success, tuple(objectives), tuple(sorted(observed_state)), len(selection.ranked), recommendation)
        with sqlite3.connect(self.db_file) as conn:
            conn.execute('INSERT INTO plan_feedback VALUES (?, ?)', (feedback.feedback_id, json.dumps(asdict(feedback), ensure_ascii=False)))
        return feedback

    def list(self) -> list[PlanFeedback]:
        with sqlite3.connect(self.db_file) as conn:
            rows = conn.execute('SELECT payload FROM plan_feedback ORDER BY rowid').fetchall()
        return [PlanFeedback(**json.loads(row[0])) for row in rows]
