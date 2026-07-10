from datetime import datetime

from src.cleaning import CleanedProject, clean_project
from src.ingestion import ingest_workbook
from src.metrics import (
    compute_blockers,
    compute_milestone_health,
    compute_schedule_slippage,
    compute_stakeholder_sentiment,
)


def _empty_project(summary=None, task_rows=None, comments=None):
    return CleanedProject(
        project_file="synthetic.xlsx",
        task_rows=task_rows or [],
        comments=comments or [],
        summary=summary or {},
        data_gaps=[],
        root_row=None,
    )


def test_schedule_slippage_defaults_neutral_without_summary_dates():
    result = compute_schedule_slippage(_empty_project(summary={}))
    assert result["score"] == 50
    assert result["data_gaps"]


def test_schedule_slippage_penalizes_behind_schedule_project():
    summary = {
        "todays_date": datetime(2026, 6, 1),
        "project_start_date": datetime(2026, 1, 1),
        "project_end_date": datetime(2026, 12, 31),
        "pct_complete": 0.1,  # way behind: ~41% of time elapsed but only 10% done
    }
    result = compute_schedule_slippage(_empty_project(summary=summary))
    assert result["score"] < 100


def test_schedule_slippage_full_marks_when_ahead_of_plan():
    summary = {
        "todays_date": datetime(2026, 6, 1),
        "project_start_date": datetime(2026, 1, 1),
        "project_end_date": datetime(2026, 12, 31),
        "pct_complete": 0.9,
    }
    result = compute_schedule_slippage(_empty_project(summary=summary))
    assert result["score"] == 100


def test_milestone_health_neutral_when_no_milestones_found():
    result = compute_milestone_health(_empty_project(summary={"todays_date": datetime(2026, 1, 1)}))
    assert result["score"] == 50
    assert result["milestone_count"] == 0
    assert result["data_gaps"]


def test_milestone_health_penalizes_overdue_milestone():
    rows = [{
        "level": 1, "phase_milestone": "Go Live", "status": "In Progress",
        "baseline_finish": datetime(2026, 1, 1), "task_name": "Go Live",
    }]
    summary = {"todays_date": datetime(2026, 1, 21)}  # 20 days overdue
    result = compute_milestone_health(_empty_project(summary=summary, task_rows=rows))
    assert result["milestone_count"] == 1
    assert len(result["overdue_milestones"]) == 1
    assert result["score"] < 100


def test_blockers_score_worsens_with_more_open_items():
    todays = datetime(2026, 6, 1)
    clean_rows = [{"_row_id": i, "status": "Not Started", "on_hold": False,
                    "status_comment": None, "predecessor_row_ids": []} for i in range(10)]
    blocked_rows = [{"_row_id": i, "status": "Not Started", "on_hold": True,
                       "status_comment": None, "predecessor_row_ids": []} for i in range(10, 15)]
    clean_score = compute_blockers(_empty_project(summary={"todays_date": todays}, task_rows=clean_rows))
    blocked_score = compute_blockers(
        _empty_project(summary={"todays_date": todays}, task_rows=clean_rows + blocked_rows)
    )
    assert blocked_score["score"] < clean_score["score"]


def test_sentiment_matches_analyzer_neutral_default():
    result = compute_stakeholder_sentiment(_empty_project(comments=[]))
    assert result["score"] == 50
    assert result["data_gaps"]


def test_real_files_produce_visibly_different_metrics(s2p_path, plan_b_path):
    s2p = clean_project(ingest_workbook(s2p_path))
    plan_b = clean_project(ingest_workbook(plan_b_path))

    s2p_milestones = compute_milestone_health(s2p)
    plan_b_milestones = compute_milestone_health(plan_b)
    assert s2p_milestones["milestone_count"] == 10
    assert plan_b_milestones["milestone_count"] == 0

    s2p_sentiment = compute_stakeholder_sentiment(s2p)
    plan_b_sentiment = compute_stakeholder_sentiment(plan_b)
    assert s2p_sentiment["comment_count"] == 9
    assert plan_b_sentiment["comment_count"] == 0
