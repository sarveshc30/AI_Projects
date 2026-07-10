"""Renders a per-project, per-week Markdown report from templates/weekly_report.md.j2."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

from src.cleaning import CleanedProject
from src.llm_reasoner import RAGReasoning
from src.metrics import ProjectMetrics
from src.rag_engine import RagResult

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "outputs" / "weekly"


def _slugify(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")


def project_slug(project: CleanedProject) -> str:
    return _slugify(Path(project.project_file).stem)


def build_report_context(
    project: CleanedProject,
    metrics: ProjectMetrics,
    rag_result: RagResult,
    llm_reasoning: Optional[RAGReasoning],
    llm_error: Optional[str],
    generated_at: Optional[datetime] = None,
) -> dict[str, Any]:
    todays_date = project.summary.get("todays_date")
    seen: set[str] = set()
    all_data_gaps = []
    for gap in list(project.data_gaps) + metrics.all_data_gaps:
        if gap not in seen:
            seen.add(gap)
            all_data_gaps.append(gap)
    return {
        "project_name": project.project_display_name,
        "source_file": project.project_file,
        "generated_at": (generated_at or datetime.now()).strftime("%Y-%m-%d %H:%M"),
        "todays_date": todays_date.strftime("%Y-%m-%d") if todays_date else None,
        "final_status": rag_result.final_status,
        "threshold_status": rag_result.threshold_status,
        "composite_score": rag_result.composite_score,
        "sub_scores": rag_result.sub_scores,
        "overrides_triggered": rag_result.overrides_triggered,
        "llm_reasoning": llm_reasoning,
        "llm_error": llm_error,
        "data_gaps": all_data_gaps,
        "schedule_detail": metrics.schedule,
        "milestone_detail": metrics.milestone,
        "blockers_detail": metrics.blockers,
        "sentiment_detail": metrics.sentiment,
    }


def render_weekly_report(context: dict[str, Any]) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("weekly_report.md.j2")
    return template.render(**context)


def write_weekly_report(
    project: CleanedProject,
    metrics: ProjectMetrics,
    rag_result: RagResult,
    llm_reasoning: Optional[RAGReasoning],
    llm_error: Optional[str],
    as_of_date: Optional[datetime] = None,
    output_root: Path = OUTPUT_ROOT,
) -> Path:
    context = build_report_context(project, metrics, rag_result, llm_reasoning, llm_error, as_of_date)
    rendered = render_weekly_report(context)

    date_str = (as_of_date or datetime.now()).strftime("%Y-%m-%d")
    out_dir = output_root / project_slug(project)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{date_str}.md"
    out_path.write_text(rendered, encoding="utf-8")
    return out_path
