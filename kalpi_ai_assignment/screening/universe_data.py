# file: screening/universe_data.py
"""Loads the bundled NSE universe constituent snapshot (data/universe_snapshot.json,
refreshed periodically by scripts/refresh_universe_snapshot.py) and resolves a
universe name (from kalpi_strategy_builder.universes_constant) to its ticker list.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "universe_snapshot.json"


@lru_cache(maxsize=1)
def _load_snapshot() -> dict:
    if not SNAPSHOT_PATH.exists():
        return {"generated_at": None, "source": None, "universes": {}}
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def snapshot_generated_at() -> str | None:
    return _load_snapshot().get("generated_at")


def resolve_universe(universe: str) -> list[dict]:
    """Returns a list of {symbol, yf_ticker, company_name, isin} for the given
    universe name. Keys match kalpi_strategy_builder.universes_constant verbatim."""
    return _load_snapshot().get("universes", {}).get(universe, [])
