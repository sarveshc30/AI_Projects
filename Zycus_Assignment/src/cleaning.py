"""Type coercion, explicit-null normalization, and task-tree reconstruction.

Guiding rule: `#UNPARSEABLE` and blank cells become Python `None`, never 0 or a guessed
default. Anywhere a value can't be coerced to its expected type, it becomes `None` too --
the caller (metrics.py) is responsible for surfacing that as a reported data gap.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from src.ingestion import IngestionResult, load_column_mapping

_DURATION_RE = re.compile(r"^-?\d+(\.\d+)?")
_PREDECESSOR_REF_RE = re.compile(r"^\s*(\d+)")

# Checkbox-style columns: populated with True when checked, blank when unchecked.
# Blank here means "false", not "unknown" -- distinct from other fields where blank
# means missing data. Documented in DECISIONS.md.
_CHECKBOX_FIELDS = {"on_hold", "not_applicable", "critical"}


def _is_null_token(value: Any, null_tokens: set[str]) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() in null_tokens:
        return True
    return False


def _clean_value(field: str, value: Any, null_tokens: set[str]) -> Any:
    if field in _CHECKBOX_FIELDS:
        return bool(value) if value is not None else False
    if _is_null_token(value, null_tokens):
        return None
    return value


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = _DURATION_RE.match(value.strip())
        if m:
            return float(m.group(0))
    return None


def _parse_date(value: Any) -> Optional[datetime]:
    return value if isinstance(value, datetime) else None


def parse_predecessor_refs(raw: Any) -> list[int]:
    """Extract leading row-number references from a Predecessors cell.

    Values look like '226', '271', '263FS +1d', '292, 293FS +2d'. We parse each
    comma-separated token's leading integer and ignore FS/FF/SS/lag-day suffixes --
    a documented simplification, not a full CPM dependency-type engine.
    """
    if not raw or not isinstance(raw, str):
        return []
    refs = []
    for token in raw.split(","):
        m = _PREDECESSOR_REF_RE.match(token)
        if m:
            refs.append(int(m.group(1)))
    return refs


class CleanedProject:
    def __init__(
        self,
        project_file: str,
        task_rows: list[dict[str, Any]],
        comments: list[dict[str, Any]],
        summary: dict[str, Any],
        data_gaps: list[str],
        root_row: Optional[dict[str, Any]],
    ):
        self.project_file = project_file
        self.task_rows = task_rows
        self.comments = comments
        self.summary = summary
        self.data_gaps = data_gaps
        self.root_row = root_row

    @property
    def project_display_name(self) -> str:
        if self.root_row and self.root_row.get("task_name"):
            return self.root_row["task_name"]
        return self.project_file


def _build_task_tree(rows: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Attach parent_row_id/children_row_ids using Level as a depth stack; return root row."""
    stack: list[dict[str, Any]] = []  # rows currently "open" at each depth
    for row in rows:
        level = row.get("level")
        row["children_row_ids"] = []
        row["parent_row_id"] = None
        if level is None:
            continue
        while stack and stack[-1].get("level") is not None and stack[-1]["level"] >= level:
            stack.pop()
        if stack:
            parent = stack[-1]
            row["parent_row_id"] = parent["_row_id"]
            parent["children_row_ids"].append(row["_row_id"])
        stack.append(row)

    if not rows:
        return None
    min_level = min((r["level"] for r in rows if r.get("level") is not None), default=None)
    if min_level is None:
        return None
    for row in rows:
        if row.get("level") == min_level:
            return row
    return None


def clean_project(ingestion_result: IngestionResult, mapping: Optional[dict] = None) -> CleanedProject:
    mapping = mapping or load_column_mapping()
    null_tokens = set(mapping.get("null_tokens", []))
    data_gaps = list(ingestion_result.data_gaps)

    cleaned_rows = []
    for row in ingestion_result.task_rows:
        cleaned: dict[str, Any] = {}
        for field, value in row.items():
            if field.startswith("_"):
                cleaned[field] = value
                continue
            cleaned[field] = _clean_value(field, value, null_tokens)

        cleaned["pct_complete"] = _parse_number(cleaned.get("pct_complete"))
        cleaned["duration_days"] = _parse_number(cleaned.get("duration"))
        cleaned["total_float"] = _parse_number(cleaned.get("total_float"))
        cleaned["variance_days"] = _parse_number(cleaned.get("variance"))
        cleaned["level"] = (
            int(cleaned["level"]) if isinstance(cleaned.get("level"), (int, float)) else None
        )
        for date_field in ("start_date", "end_date", "baseline_start", "baseline_finish",
                           "actual_start", "actual_finish"):
            cleaned[date_field] = _parse_date(cleaned.get(date_field))
        cleaned["predecessor_row_ids"] = parse_predecessor_refs(row.get("predecessors"))

        cleaned_rows.append(cleaned)

    root_row = _build_task_tree(cleaned_rows)

    cleaned_comments = []
    for c in ingestion_result.comments:
        cc = {k: _clean_value("comment_" + k, v, null_tokens) for k, v in c.items()}
        cleaned_comments.append(cc)

    cleaned_summary = {}
    for k, v in ingestion_result.summary.items():
        if k == "_unmapped":
            cleaned_summary[k] = v
            continue
        cleaned_summary[k] = _clean_value(k, v, null_tokens)
    for numeric_key in ("not_started_count", "in_progress_count", "completed_count",
                        "on_hold_count", "duration"):
        if numeric_key in cleaned_summary:
            cleaned_summary[numeric_key] = _parse_number(cleaned_summary[numeric_key])
    if "pct_complete" in cleaned_summary:
        cleaned_summary["pct_complete"] = _parse_number(cleaned_summary["pct_complete"])
    for date_key in ("project_start_date", "project_end_date", "todays_date"):
        if date_key in cleaned_summary:
            cleaned_summary[date_key] = _parse_date(cleaned_summary[date_key])

    if cleaned_summary.get("todays_date") is None:
        data_gaps.append(
            "Summary sheet's \"Today's Date\" is missing/unparseable; schedule-slippage "
            "calculations cannot use the as-of date the brief requires and will be skipped."
        )

    return CleanedProject(
        ingestion_result.project_file, cleaned_rows, cleaned_comments, cleaned_summary,
        data_gaps, root_row,
    )
