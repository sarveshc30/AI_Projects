from src.metrics import ProjectMetrics
from src.rag_engine import compute_rag_status


def _metrics(schedule=100, milestone=100, blockers=100, sentiment=100,
             overdue_milestones=None, critical_negative_float_count=0, status_comment_count=0):
    return ProjectMetrics(
        schedule={"score": schedule, "critical_negative_float_count": critical_negative_float_count,
                    "critical_negative_float_tasks": [], "data_gaps": []},
        milestone={"score": milestone, "overdue_milestones": overdue_milestones or [], "data_gaps": []},
        blockers={"score": blockers, "status_comment_count": status_comment_count, "data_gaps": []},
        sentiment={"score": sentiment, "data_gaps": []},
    )


def test_thresholds_green():
    result = compute_rag_status(_metrics(100, 100, 100, 100))
    assert result.final_status == "Green"
    assert result.composite_score == 100


def test_thresholds_amber():
    result = compute_rag_status(_metrics(70, 70, 70, 70))
    assert result.threshold_status == "Amber"
    assert result.final_status == "Amber"


def test_thresholds_red_without_override():
    result = compute_rag_status(_metrics(30, 30, 30, 30))
    assert result.final_status == "Red"
    assert not result.override_applied


def test_milestone_override_forces_red_even_with_good_composite():
    overdue = [{"task_name": "Go Live", "phase_milestone": "Go Live", "days_overdue": 25, "status": "In Progress"}]
    result = compute_rag_status(_metrics(90, 90, 90, 90, overdue_milestones=overdue))
    assert result.threshold_status == "Green"
    assert result.final_status == "Red"
    assert result.override_applied


def test_milestone_overdue_within_threshold_does_not_override():
    overdue = [{"task_name": "Go Live", "phase_milestone": "Go Live", "days_overdue": 5, "status": "In Progress"}]
    result = compute_rag_status(_metrics(90, 90, 90, 90, overdue_milestones=overdue))
    assert not result.override_applied
    assert result.final_status == "Green"


def test_critical_negative_float_without_recovery_plan_forces_red():
    result = compute_rag_status(_metrics(90, 90, 90, 90, critical_negative_float_count=2, status_comment_count=0))
    assert result.override_applied
    assert result.final_status == "Red"


def test_critical_negative_float_with_documented_recovery_plan_does_not_override():
    result = compute_rag_status(_metrics(90, 90, 90, 90, critical_negative_float_count=2, status_comment_count=3))
    assert not result.override_applied
    assert result.final_status == "Green"


def test_weights_sum_to_one():
    from src.rag_engine import WEIGHTS
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
