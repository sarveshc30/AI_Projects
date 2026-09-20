"""
src/__main__.py
───────────────
Allows running the package directly with ``python -m src``.
Delegates to the CLI entry point.
"""

from src.cli import main

if __name__ == "__main__":
    main()
