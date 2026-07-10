"""CLI entrypoint: run the full weekly pipeline against one or more project plan workbooks.

Usage:
    python src/run_weekly.py data/samples/S2P_Project.xlsx data/samples/Project_Plan_B.xlsx
    python src/run_weekly.py --all   # runs every .xlsx in data/samples/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import run_pipeline_for_file  # noqa: E402
from src.sentiment import SentimentAnalyzer  # noqa: E402

DEFAULT_SAMPLES_DIR = Path(__file__).resolve().parent.parent / "data" / "samples"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run weekly project health reports.")
    parser.add_argument("files", nargs="*", help="Path(s) to project plan .xlsx files.")
    parser.add_argument("--all", action="store_true", help="Run every .xlsx in data/samples/.")
    args = parser.parse_args()

    if args.all or not args.files:
        files = sorted(DEFAULT_SAMPLES_DIR.glob("*.xlsx"))
    else:
        files = [Path(f) for f in args.files]

    if not files:
        print("No project plan files found.")
        return

    analyzer = SentimentAnalyzer()
    for f in files:
        print(f"Processing {f} ...")
        result = run_pipeline_for_file(f, sentiment_analyzer=analyzer)
        print(
            f"  -> RAG status: {result.rag_result.final_status} "
            f"(composite {result.rag_result.composite_score}, "
            f"threshold-only {result.rag_result.threshold_status})"
        )
        print(f"  -> Report written to {result.report_path}")
        if result.llm_error:
            print(f"  -> LLM narrative unavailable this run: {result.llm_error}")


if __name__ == "__main__":
    main()
