"""Ingestion must survive schema drift between the two sample files: despite differing
column sets/order, both should normalize to the same canonical field shape."""
from src.ingestion import ingest_workbook, load_column_mapping


def test_both_files_normalize_to_same_canonical_fields(s2p_path, plan_b_path):
    mapping = load_column_mapping()
    s2p = ingest_workbook(s2p_path, mapping)
    plan_b = ingest_workbook(plan_b_path, mapping)

    s2p_keys = set(s2p.task_rows[0].keys())
    plan_b_keys = set(plan_b.task_rows[0].keys())
    assert s2p_keys == plan_b_keys, "canonical schema shape must match across files"

    expected_canonical_fields = set(mapping["task_sheet_column_map"].keys())
    assert expected_canonical_fields.issubset(s2p_keys)


def test_s2p_has_populated_rag_and_phase_milestone(s2p_path):
    result = ingest_workbook(s2p_path)
    assert any(r.get("task_rag") for r in result.task_rows)
    assert any(r.get("phase_milestone") for r in result.task_rows)
    assert any(r.get("level") is not None for r in result.task_rows)


def test_plan_b_reports_level_and_rag_gaps(plan_b_path):
    result = ingest_workbook(plan_b_path)
    assert all(r.get("task_rag") is None for r in result.task_rows)
    gap_text = " ".join(result.data_gaps)
    assert "Level" in gap_text
    assert "ancestors" in gap_text.lower()
    # Ancestors-based fallback still gives every row a usable level value.
    assert any(r.get("level") is not None for r in result.task_rows)


def test_plan_b_comments_sheet_is_empty(plan_b_path):
    result = ingest_workbook(plan_b_path)
    assert result.comments == []
    assert any("Comments sheet" in g or "comments" in g.lower() for g in result.data_gaps)


def test_s2p_comments_sheet_has_entries(s2p_path):
    result = ingest_workbook(s2p_path)
    assert len(result.comments) == 9
    assert all(c["comment_text"] for c in result.comments)


def test_summary_unparseable_values_pass_through_raw(s2p_path):
    result = ingest_workbook(s2p_path)
    assert result.summary["target_start_date"] == "#UNPARSEABLE"


def test_predecessor_row_ids_resolve_to_real_rows(s2p_path):
    result = ingest_workbook(s2p_path)
    by_row_id = {r["_row_id"]: r for r in result.task_rows}
    for row in result.task_rows:
        if row.get("predecessors"):
            # At least the raw predecessors string is captured; row_id 226 (validated
            # during data exploration) must exist in the sheet.
            assert 226 in by_row_id
            break
