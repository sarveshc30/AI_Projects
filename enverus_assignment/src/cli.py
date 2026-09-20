"""
src/cli.py
──────────
Interactive REPL chatbot CLI for the PDF RAG system.

Usage:
    python src/cli.py            # auto-ingest on first run, then REPL
    python src/cli.py --k 6      # default k=6 for this session
    python src/cli.py --reset    # force re-ingest before starting REPL
    python src/cli.py --batch    # non-interactive: run all 15 assignment questions

In the REPL you can also override k per-question:
    > What is DevAI? --k 6
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# Ensure the project root is on sys.path when run as `python src/cli.py`
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config import DEFAULT_PDF, TOP_K
from src.ingest import ingest
from src.logging_utils import log_qa
from src.rag_chain import answer_question
from src.retriever import collection_is_populated

app = typer.Typer(add_completion=False, help="PDF RAG Chatbot — Agent-as-a-Judge paper.")
console = Console()

# ── 15 assignment questions (Appendix A) ──────────────────────────────────────
ASSIGNMENT_QUESTIONS: list[tuple[int, str]] = [
    (4,  "What is the DevAI dataset, and how many tasks, requirements, and preferences does it contain?"),
    (5,  "What percentage of evaluation time and cost does Agent-as-a-Judge save compared to using three human experts?"),
    (6,  "According to Section 4.4 (Cost Analysis), how much did Agent-as-a-Judge cost and how long did it take, compared to Human-as-a-Judge?"),
    (7,  "Which three open-source agentic frameworks were benchmarked on DevAI?"),
    (8,  "What is the average cost and average time for OpenHands?"),
    (9,  "Which system is the most cost-efficient and which is the most expensive?"),
    (10, "What was GPT-Pilot's 'Requirements Met (Independent)' percentage under Human-as-a-Judge?"),
    (11, "What was MetaGPT's Task Solve Rate?"),
    (12, "In the black-box setting, what Alignment Rate did Agent-as-a-Judge vs. LLM-as-a-Judge achieve when evaluating OpenHands?"),
    (13, "What alignment rate does Agent-as-a-Judge achieve using only the 'ask' component, and after adding 'graph,' 'read,' and 'locate'?"),
    (14, "Which search algorithm (BM2.5, Sentence-BERT, Fuzzy Search, or no search module) gave the best alignment rate?"),
    (15, "Which two model architectures are mentioned most frequently in the DevAI user queries?"),
    (16, "What is requirement R1 in the 'Devin AI Software Engineer Plants Secret Messages in Images' task?"),
    (17, "Which of the three human evaluators (231a, 38bb, cn9o) made the most errors when judging GPT-Pilot, and what was the error rate?"),
    (18, "In the diagram comparing LLM-as-a-Judge, Agent-as-a-Judge, and Human-as-a-Judge, what key drawback is highlighted for Human-as-a-Judge?"),
]

# Questions that target specific tables/figures benefit from more chunks
_HIGH_K_QUESTIONS = {6, 8, 9, 10, 11, 12, 13, 14, 17}


def _ensure_index(reset: bool = False) -> None:
    """Auto-ingest the PDF if the Chroma collection is empty or reset is True."""
    if reset or not collection_is_populated():
        console.print("\n[bold yellow]⚙  Ingesting PDF into ChromaDB…[/bold yellow]")
        ingest(pdf_path=DEFAULT_PDF, reset=reset)
    else:
        console.print("[dim]✓ ChromaDB collection ready.[/dim]")


def _parse_k_override(question: str, default_k: int) -> tuple[str, int]:
    """Extract optional ``--k N`` suffix from a question string.

    Returns:
        (cleaned_question, effective_k)
    """
    match = re.search(r"\s*--k\s+(\d+)\s*$", question, re.IGNORECASE)
    if match:
        k = int(match.group(1))
        question = question[: match.start()].strip()
        return question, k
    return question.strip(), default_k


def _print_result(result, k: int) -> None:
    """Pretty-print the answer + retrieved chunks to the terminal."""
    console.print()
    console.print(Panel(
        Markdown(result.answer),
        title="[bold green]Answer[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))

    console.print()
    console.print(Rule(f"[bold cyan]Retrieved Chunks (k={k})[/bold cyan]"))
    for i, chunk in enumerate(result.sources, start=1):
        header = Text(
            f"[Chunk {i}/{len(result.sources)}]  "
            f"Page {chunk.page}  |  ID: {chunk.chunk_id}  |  "
            f"Distance: {chunk.distance:.4f}",
            style="bold magenta",
        )
        console.print(header)
        console.print(Panel(chunk.text.strip(), border_style="dim"))
    console.print()


# ── Typer commands ─────────────────────────────────────────────────────────────

@app.command()
def chat(
    k: int = typer.Option(TOP_K, "--k", help="Number of chunks to retrieve per question."),
    reset: bool = typer.Option(False, "--reset", help="Force re-ingest the PDF before starting."),
) -> None:
    """Start the interactive REPL chatbot."""
    _ensure_index(reset=reset)

    console.print(Panel(
        "[bold]PDF RAG Chatbot[/bold]\n"
        "Ask questions about the [italic]Agent-as-a-Judge[/italic] paper.\n\n"
        "  • Override k per-question:  [cyan]What is DevAI? --k 6[/cyan]\n"
        "  • Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to close.",
        title="[bold blue]✓ Ready[/bold blue]",
        border_style="blue",
    ))

    while True:
        try:
            raw = console.input("\n[bold blue]>[/bold blue] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not raw:
            continue
        if raw.lower() in {"exit", "quit", "q"}:
            console.print("[dim]Goodbye![/dim]")
            break

        question, effective_k = _parse_k_override(raw, k)

        console.print(f"[dim]Retrieving {effective_k} chunks…[/dim]")
        result = answer_question(question, k=effective_k)
        _print_result(result, effective_k)
        log_qa(result)
        console.print("[dim](Logged to answers/qa_chunks.md)[/dim]")


@app.command()
def batch(
    k: int = typer.Option(TOP_K, "--k", help="Default number of chunks (overridden for table-heavy questions)."),
    reset: bool = typer.Option(False, "--reset", help="Force re-ingest before running."),
) -> None:
    """Run all 15 assignment questions non-interactively and log results."""
    _ensure_index(reset=reset)

    console.print(Panel(
        "[bold]Batch mode[/bold] — running all 15 assignment questions.\n"
        "Results are logged to [cyan]answers/qa_chunks.md[/cyan].",
        title="[bold blue]Batch Run[/bold blue]",
        border_style="blue",
    ))

    for q_num, question in ASSIGNMENT_QUESTIONS:
        effective_k = max(k, 6) if q_num in _HIGH_K_QUESTIONS else k
        console.print(f"\n[bold cyan]Q{q_num}[/bold cyan] (k={effective_k}): {question}")
        console.print("[dim]Retrieving…[/dim]")

        result = answer_question(question, k=effective_k)
        _print_result(result, effective_k)
        log_qa(result)

    console.print(Panel(
        "All 15 questions answered.\n"
        "See [cyan]answers/qa_chunks.md[/cyan] for the full log.",
        title="[bold green]✓ Batch Complete[/bold green]",
        border_style="green",
    ))


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point when run as ``python src/cli.py`` (defaults to chat command)."""
    # If no sub-command is given, default to `chat`
    if len(sys.argv) == 1 or (len(sys.argv) >= 2 and sys.argv[1].startswith("--")):
        sys.argv.insert(1, "chat")
    app()


if __name__ == "__main__":
    main()
