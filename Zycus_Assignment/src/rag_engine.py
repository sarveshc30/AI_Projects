"""Deterministic RAG engine: weighted composite -> threshold mapping -> hard overrides.

Pure code, zero external dependencies (no LLM). This is the audit trail: it must produce
the same result every time, whether or not the LLM narrative layer (llm_reasoner.py) is
reachable.
"""
from __future__ import annotations

from typing import Any

from src.metrics import ProjectMetrics

WEIGHTS = {
    "schedule": 0.35,
    "milestone": 0.30,
    "blockers": 0.20,
    "sentiment": 0.15,
}

GREEN_THRESHOLD = 80
AMBER_THRESHOLD = 60

DEFAULT_MILESTONE_OVERDUE_OVERRIDE_DAYS = 10


def _threshold_status(composite: float) -> str:
    if composite >= GREEN_THRESHOLD:
        return "Green"
    if composite >= AMBER_THRESHOLD:
        return "Amber"
    return "Red"


class RagResult:
    def __init__(
        self,
        composite_score: float,
        threshold_status: str,
        final_status: str,
        overrides_triggered: list[str],
        sub_scores: dict[str, float],
    ):
        self.composite_score = composite_score
        self.threshold_status = threshold_status
        self.final_status = final_status
        self.overrides_triggered = overrides_triggered
        self.sub_scores = sub_scores

    @property
    def override_applied(self) -> bool:
        return bool(self.overrides_triggered)


def compute_rag_status(
    metrics: ProjectMetrics,
    milestone_overdue_override_days: int = DEFAULT_MILESTONE_OVERDUE_OVERRIDE_DAYS,
) -> RagResult:
    sub_scores = {
        "schedule": metrics.schedule["score"],
        "milestone": metrics.milestone["score"],
        "blockers": metrics.blockers["score"],
        "sentiment": metrics.sentiment["score"],
    }
    composite = round(sum(sub_scores[k] * WEIGHTS[k] for k in WEIGHTS), 1)
    threshold_status = _threshold_status(composite)

    overrides_triggered: list[str] = []

    overdue_milestones = metrics.milestone.get("overdue_milestones", [])
    severely_overdue = [
        m for m in overdue_milestones if m["days_overdue"] > milestone_overdue_override_days
    ]
    if severely_overdue:
        names = ", ".join(
            m.get("task_name") or m.get("phase_milestone") or "unnamed milestone"
            for m in severely_overdue
        )
        overrides_triggered.append(
            f"Milestone(s) overdue by more than {milestone_overdue_override_days} days without "
            f"completion: {names}."
        )

    critical_negative_float_count = metrics.schedule.get("critical_negative_float_count", 0)
    if critical_negative_float_count > 0:
        # Status Comment is the only place a "documented recovery plan" could live. If the
        # source file has zero non-empty Status Comment rows anywhere (true for both sample
        # files), no recovery plan can ever be considered documented for these tasks.
        has_any_status_comment = metrics.blockers.get("status_comment_count", 0) > 0
        if not has_any_status_comment:
            names = ", ".join(metrics.schedule.get("critical_negative_float_tasks", []))
            overrides_triggered.append(
                "Critical-path task(s) with negative float and no documented recovery plan in "
                f"Status Comment: {names}."
            )

    final_status = "Red" if overrides_triggered else threshold_status

    return RagResult(composite, threshold_status, final_status, overrides_triggered, sub_scores)
