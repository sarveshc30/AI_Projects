from src.cleaning import clean_project, parse_predecessor_refs
from src.ingestion import ingest_workbook


def test_unparseable_and_blank_become_none(s2p_path):
    cleaned = clean_project(ingest_workbook(s2p_path))
    assert cleaned.summary["target_start_date"] is None
    assert cleaned.summary["target_end_date"] is None


def test_duration_and_variance_parsed_to_numbers(s2p_path):
    cleaned = clean_project(ingest_workbook(s2p_path))
    rows_with_duration = [r for r in cleaned.task_rows if r.get("duration_days") is not None]
    assert rows_with_duration
    assert all(isinstance(r["duration_days"], float) for r in rows_with_duration)


def test_checkbox_fields_default_to_false_not_none(s2p_path):
    cleaned = clean_project(ingest_workbook(s2p_path))
    for row in cleaned.task_rows:
        assert row["on_hold"] in (True, False)
        assert row["critical"] in (True, False)
    assert any(r["on_hold"] for r in cleaned.task_rows)
    assert any(r["critical"] for r in cleaned.task_rows)


def test_project_display_name_derived_from_root_row(s2p_path, plan_b_path):
    s2p = clean_project(ingest_workbook(s2p_path))
    plan_b = clean_project(ingest_workbook(plan_b_path))
    assert "Titan" in s2p.project_display_name
    assert "UniSan" in plan_b.project_display_name


def test_todays_date_parsed_as_datetime(s2p_path):
    cleaned = clean_project(ingest_workbook(s2p_path))
    assert cleaned.summary["todays_date"].year == 2026


def test_parse_predecessor_refs_ignores_lag_suffix():
    assert parse_predecessor_refs("263FS +1d") == [263]
    assert parse_predecessor_refs("292, 293FS +2d") == [292, 293]
    assert parse_predecessor_refs(None) == []
    assert parse_predecessor_refs("") == []


def test_predecessor_row_ids_populated_on_rows(plan_b_path):
    cleaned = clean_project(ingest_workbook(plan_b_path))
    rows_with_preds = [r for r in cleaned.task_rows if r.get("predecessor_row_ids")]
    assert rows_with_preds
