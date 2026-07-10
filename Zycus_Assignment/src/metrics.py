"""Computes the four raw 0-100 RAG sub-scores per docs/RAG_Methodology.md.

Every function here returns both a score and a detail dict describing exactly what was
(and wasn't) computable, so gaps propagate to the final report instead of being silently
absorbed into a number.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from src.cleaning import CleanedProject
from src.sentiment import SentimentAnalyzer

# Scaling constants (implementation detail; the four signals/weights themselves come
# directly from the brief and are NOT tunable here -- only how raw counts map to 0-100).
FLOAT_PENALTY_PER_CRITICAL_NEGATIVE_ROW = 8
MILESTONE_OVERDUE_PENALTY_PER_DAY = 2.5
BLOCKER_RATIO_SCALE = 400  # 25% of tasks flagged as open items -> score floor of 0
NEUTRAL_DEFAULT = 50


def _clamp(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))


def compute_schedule_slippage(project: CleanedProject) -> dict[str, Any]:
    summary = project.summary
    todays_date = summary.get("todays_date")
    start = summary.get("project_start_date")
    end = summary.get("project_end_date")
    actual_pct = summary.get("pct_complete")

    data_gaps: list[str] = []
    if not (todays_date and start and end and actual_pct is not None):
        missing = [
            n for n, v in (("Today's Date", todays_date), ("Project Start Date", start),
                            ("Project End Date", end), ("% Complete", actual_pct)) if not v
        ]
        data_gaps.append(
            "Schedule slippage sub-score defaulted to neutral: Summary sheet missing "
            + ", ".join(missing) + "."
        )
        expected_pct = None
        base_score = NEUTRAL_DEFAULT
    else:
        total_days = (end - start).days
        elapsed_days = (todays_date - start).days
        expected_pct = _clamp(elapsed_days / total_days, 0, 1) if total_days > 0 else None
        if expected_pct is None:
            data_gaps.append(
                "Schedule slippage sub-score defaulted to neutral: project duration is zero "
                "or invalid in Summary sheet."
            )
            base_score = NEUTRAL_DEFAULT
        else:
            behind_by = max(0.0, expected_pct - actual_pct)
            base_score = _clamp(100 - behind_by * 200)

    critical_negative_float_rows = [
        r for r in project.task_rows
        if r.get("critical") and r.get("total_float") is not None and r["total_float"] < 0
    ]
    float_penalty = min(60, len(critical_negative_float_rows) * FLOAT_PENALTY_PER_CRITICAL_NEGATIVE_ROW)
    score = _clamp(base_score - float_penalty)

    return {
        "score": round(score, 1),
        "expected_pct_complete": round(expected_pct, 3) if expected_pct is not None else None,
        "actual_pct_complete": actual_pct,
        "critical_negative_float_count": len(critical_negative_float_rows),
        "critical_negative_float_tasks": [
            r["task_name"] for r in critical_negative_float_rows if r.get("task_name")
        ],
        "data_gaps": data_gaps,
    }


def _is_milestone_row(row: dict[str, Any]) -> bool:
    # "Low Level" is interpreted as <=2: empirically, milestone-tagged rows in the sample
    # data cluster at Level 1 with one exception ("Pre UAT") tagged Level 2 -- a source
    # labeling inconsistency, not a different kind of row. Level <=2 still safely excludes
    # the hundreds of leaf-level task rows (Levels go up to 8).
    level = row.get("level")
    return level is not None and level <= 2 and bool(row.get("phase_milestone"))


def compute_milestone_health(project: CleanedProject, overdue_threshold_days: int = 10) -> dict[str, Any]:
    todays_date = project.summary.get("todays_date")
    milestones = [r for r in project.task_rows if _is_milestone_row(r)]

    data_gaps: list[str] = []
    if not milestones:
        data_gaps.append(
            "Milestone health sub-score defaulted to neutral: no rows matched the milestone "
            "rule (populated Phase/Milestone at Level 1). This source file may not tag "
            "milestones the same way as other project plans."
        )
        return {
            "score": NEUTRAL_DEFAULT,
            "milestone_count": 0,
            "overdue_milestones": [],
            "data_gaps": data_gaps,
        }

    if not todays_date:
        data_gaps.append(
            "Milestone health sub-score defaulted to neutral: Summary sheet's Today's Date "
            "is unavailable, so overdue status can't be evaluated."
        )
        return {
            "score": NEUTRAL_DEFAULT,
            "milestone_count": len(milestones),
            "overdue_milestones": [],
            "data_gaps": data_gaps,
        }

    overdue = []
    for m in milestones:
        baseline_finish = m.get("baseline_finish")
        if not baseline_finish:
            continue
        if m.get("status") != "Completed" and baseline_finish < todays_date:
            days_overdue = (todays_date - baseline_finish).days
            overdue.append({
                "task_name": m.get("task_name"),
                "phase_milestone": m.get("phase_milestone"),
                "days_overdue": days_overdue,
                "status": m.get("status"),
            })

    penalty = sum(min(40, o["days_overdue"] * MILESTONE_OVERDUE_PENALTY_PER_DAY) for o in overdue)
    score = _clamp(100 - penalty)

    return {
        "score": round(score, 1),
        "milestone_count": len(milestones),
        "overdue_milestones": overdue,
        "data_gaps": data_gaps,
    }


def compute_blockers(project: CleanedProject) -> dict[str, Any]:
    rows = project.task_rows
    by_row_id = {r["_row_id"]: r for r in rows}
    todays_date = project.summary.get("todays_date")

    data_gaps: list[str] = []

    status_comment_rows = [r for r in rows if r.get("status_comment")]
    if not status_comment_rows:
        data_gaps.append(
            "'Status Comment' column is empty for every row in this file; the blockers "
            "signal falls back to On Hold flags and predecessor-overdue detection only."
        )

    on_hold_rows = [r for r in rows if r.get("on_hold")]

    predecessor_overdue_rows = []
    if todays_date:
        for r in rows:
            if r.get("status") != "Not Started":
                continue
            for pred_id in r.get("predecessor_row_ids", []):
                pred = by_row_id.get(pred_id)
                if not pred:
                    continue
                pred_finish = pred.get("baseline_finish") or pred.get("end_date")
                if pred.get("status") != "Completed" and pred_finish and pred_finish < todays_date:
                    predecessor_overdue_rows.append(r)
                    break
    else:
        data_gaps.append(
            "Today's Date unavailable; predecessor-overdue blocker detection was skipped."
        )

    open_items_count = len(status_comment_rows) + len(on_hold_rows) + len(predecessor_overdue_rows)
    total_rows = len(rows) or 1
    ratio = open_items_count / total_rows
    score = _clamp(100 - ratio * BLOCKER_RATIO_SCALE)

    return {
        "score": round(score, 1),
        "status_comment_count": len(status_comment_rows),
        "on_hold_count": len(on_hold_rows),
        "predecessor_overdue_count": len(predecessor_overdue_rows),
        "predecessor_overdue_tasks": [
            r["task_name"] for r in predecessor_overdue_rows if r.get("task_name")
        ][:10],
        "total_task_count": len(rows),
        "data_gaps": data_gaps,
    }


def compute_stakeholder_sentiment(
    project: CleanedProject, analyzer: Optional[SentimentAnalyzer] = None
) -> dict[str, Any]:
    analyzer = analyzer or SentimentAnalyzer()
    texts = [c.get("comment_text") for c in project.comments]
    result = analyzer.compute_project_sentiment(texts)
    data_gaps = [result["data_gap"]] if result.get("data_gap") else []
    return {
        "score": result["score"],
        "comment_count": result["comment_count"],
        "avg_compound": result["avg_compound"],
        "data_gaps": data_gaps,
    }


class ProjectMetrics:
    def __init__(self, schedule, milestone, blockers, sentiment):
        self.schedule = schedule
        self.milestone = milestone
        self.blockers = blockers
        self.sentiment = sentiment

    @property
    def all_data_gaps(self) -> list[str]:
        gaps = []
        for signal in (self.schedule, self.milestone, self.blockers, self.sentiment):
            gaps.extend(signal.get("data_gaps", []))
        return gaps


def compute_all_metrics(
    project: CleanedProject, analyzer: Optional[SentimentAnalyzer] = None
) -> ProjectMetrics:
    return ProjectMetrics(
        schedule=compute_schedule_slippage(project),
        milestone=compute_milestone_health(project),
        blockers=compute_blockers(project),
        sentiment=compute_stakeholder_sentiment(project, analyzer),
    )
