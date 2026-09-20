"""Timestamped console logging in the format the problem statement's sample run shows."""

import sys
from datetime import datetime

BANNER_WIDTH = 70


def _stamp():
    return datetime.now().strftime("%H:%M:%S")


def _safe(text):
    """Make text printable on a cp1252 console.

    LLM output and API error payloads routinely contain non-breaking hyphens, curly
    quotes and em dashes. Windows consoles can't encode those, and an unguarded print
    raises UnicodeEncodeError - which is fatal precisely when it is least acceptable,
    inside the warn() call on an error path that exists to keep the run alive.
    """
    text = str(text)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
        return text
    except UnicodeEncodeError:
        return text.encode(encoding, "replace").decode(encoding)


def start_banner(brand):
    print("=" * BANNER_WIDTH)
    print(f"  LEAD GEN AGENT  |  Brand: {brand}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * BANNER_WIDTH)
    print()


def end_banner(brand, ok=True):
    print()
    status = "DONE" if ok else "COMPLETED WITH ERRORS"
    print(f"  [{_stamp()}] {status}: {brand}")
    print("=" * BANNER_WIDTH)


def log(step, message):
    """Log a successful/normal step, e.g. log("discovery_agent", "found on Amazon")."""
    print(_safe(f"  [{_stamp()}] {step} -> {message}"))


def log_block(step, message, lines):
    """Log a step followed by an indented multi-line block (e.g. the category tree).

    Windows consoles default to cp1252, which can't encode the box-drawing characters the
    tree uses; rather than crash a completed run on a cosmetic detail, fall back to ASCII
    connectors for the console only. The Markdown file is written as UTF-8 either way.
    """
    log(step, message)
    for line in lines:
        try:
            print(f"      {line}")
        except UnicodeEncodeError:
            # Box-drawing characters get readable ASCII stand-ins rather than "?".
            ascii_line = line.replace("├──", "+--").replace("└──", "`--").replace("│", "|")
            print(_safe(f"      {ascii_line}"))


def warn(step, message):
    print(_safe(f"  [{_stamp()}] {step} !! {message}"))
