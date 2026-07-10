"""Thin orchestrator wiring ingestion -> cleaning -> metrics -> RAG engine -> LLM narrative
-> report generation into a single per-project run (stages 1-6 of the build)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.cleaning import CleanedProject, clean_project
from src.ingestion import ingest_workbook, load_column_mapping
from src.llm_reasoner import RAGReasoning, get_rag_reasoning
from src.metrics import ProjectMetrics, compute_all_metrics
from src.rag_engine import RagResult, compute_rag_status
from src.report_generator import write_weekly_report
from src.sentiment import SentimentAnalyzer


class PipelineResult:
    def __init__(
        self,
        project: CleanedProject,
        metrics: ProjectMetrics,
        rag_result: RagResult,
        llm_reasoning: Optional[RAGReasoning],
        llm_error: Optional[str],
        report_path: Optional[Path],
    ):
        self.project = project
        self.metrics = metrics
        self.rag_result = rag_result
        self.llm_reasoning = llm_reasoning
        self.llm_error = llm_error
        self.report_path = report_path


def run_pipeline_for_file(
    file_path: str | Path,
    sentiment_analyzer: Optional[SentimentAnalyzer] = None,
    write_report: bool = True,
) -> PipelineResult:
    mapping = load_column_mapping()
    ingestion_result = ingest_workbook(file_path, mapping)
    project = clean_project(ingestion_result, mapping)

    analyzer = sentiment_analyzer or SentimentAnalyzer()
    metrics = compute_all_metrics(project, analyzer)
    rag_result = compute_rag_status(metrics)

    comments_sample = [c.get("comment_text") for c in project.comments][:8]
    all_data_gaps = list(project.data_gaps) + metrics.all_data_gaps
    llm_reasoning, llm_error = get_rag_reasoning(
        project.project_display_name,
        rag_result.sub_scores,
        rag_result.final_status,
        rag_result.overrides_triggered,
        all_data_gaps,
        comments_sample,
    )

    report_path = None
    if write_report:
        as_of = project.summary.get("todays_date")
        report_path = write_weekly_report(
            project, metrics, rag_result, llm_reasoning, llm_error, as_of
        )

    return PipelineResult(project, metrics, rag_result, llm_reasoning, llm_error, report_path)
