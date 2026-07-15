# file: scripts/refresh_universe_snapshot.py
"""Refreshes data/universe_snapshot.json from NSE's public index constituent CSVs.

Standalone script, not imported by the running app (so it never affects
Vercel's import-tracing / bundling). Re-run manually roughly every 3 months
to pick up index reconstitutions; could later be wired to a scheduled job
(e.g. Vercel Cron hitting a protected admin endpoint), but that's out of
scope here.

Usage:
    python scripts/refresh_universe_snapshot.py [--only "Nifty 50,Nifty 500"] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "universe_snapshot.json"

INDEX_BASE = "https://nsearchives.nseindia.com/content/indices/"
FNO_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"

INDEX_CSV_FILES: dict[str, str] = {
    "Nifty 50": "ind_nifty50list.csv",
    "Nifty Next 50": "ind_niftynext50list.csv",
    "Nifty 100": "ind_nifty100list.csv",
    "Nifty 200": "ind_nifty200list.csv",
    "Nifty 500": "ind_nifty500list.csv",
    "Nifty Total Market": "ind_niftytotalmarket_list.csv",
    "Nifty Midcap 50": "ind_niftymidcap50list.csv",
    "Nifty Midcap 100": "ind_niftymidcap100list.csv",
    "Nifty Midcap 150": "ind_niftymidcap150list.csv",
    "Nifty Smallcap 50": "ind_niftysmallcap50list.csv",
    "Nifty Smallcap 100": "ind_niftysmallcap100list.csv",
    "Nifty Smallcap 250": "ind_niftysmallcap250list.csv",
    "Nifty Microcap 250": "ind_niftymicrocap250_list.csv",
    "NIFTY MIDSMALLCAP 400": "ind_niftymidsmallcap400list.csv",
    "Nifty LargeMidcap 250": "ind_niftylargemidcap250list.csv",
}

# Index/derivative names that show up in the F&O market-lots symbol column but
# aren't individually tradable equities -- excluded from "NIFTY FNO".
_FNO_NON_EQUITY_SYMBOLS = {
    "NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50",
    "NIFTYIT", "NIFTYPSE", "NIFTYINFRA", "NIFTYPSUBANK",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    try:
        # Warm-up request for cookies; NSE routinely 403s bare/non-browser requests
        # on some endpoints even though the archive CSVs often work without it.
        s.get("https://www.nseindia.com", timeout=15)
    except requests.RequestException:
        pass
    return s


def _fetch_index_csv(session: requests.Session, filename: str) -> list[dict]:
    resp = session.get(INDEX_BASE + filename, timeout=20)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = []
    for row in reader:
        symbol = (row.get("Symbol") or "").strip()
        if not symbol:
            continue
        rows.append({
            "symbol": symbol,
            "yf_ticker": f"{symbol}.NS",
            "company_name": (row.get("Company Name") or symbol).strip(),
            "isin": (row.get("ISIN Code") or "").strip(),
        })
    return rows


def _fetch_fno_symbols(session: requests.Session, name_lookup: dict[str, dict]) -> list[dict]:
    resp = session.get(FNO_URL, timeout=20)
    resp.raise_for_status()
    reader = csv.reader(io.StringIO(resp.text))
    header = next(reader, None)
    rows = []
    seen = set()
    for row in reader:
        if not row:
            continue
        symbol = row[0].strip()
        if not symbol or symbol in seen or symbol in _FNO_NON_EQUITY_SYMBOLS:
            continue
        seen.add(symbol)
        known = name_lookup.get(symbol)
        rows.append({
            "symbol": symbol,
            "yf_ticker": f"{symbol}.NS",
            "company_name": known["company_name"] if known else symbol,
            "isin": known["isin"] if known else "",
        })
    return rows


def refresh(only: list[str] | None, dry_run: bool) -> None:
    existing = {"generated_at": None, "source": None, "universes": {}}
    if SNAPSHOT_PATH.exists():
        existing = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    universes: dict[str, list[dict]] = dict(existing.get("universes", {}))
    session = _session()

    targets = only if only else list(INDEX_CSV_FILES.keys()) + ["NIFTY FNO"]
    summary = []

    name_lookup: dict[str, dict] = {}
    for entries in universes.values():
        for e in entries:
            name_lookup[e["symbol"]] = e

    for universe_name in targets:
        prev_count = len(universes.get(universe_name, []))
        try:
            if universe_name == "NIFTY FNO":
                # Build name_lookup fresh from whatever index lists we already have/fetched
                for entries in universes.values():
                    for e in entries:
                        name_lookup[e["symbol"]] = e
                rows = _fetch_fno_symbols(session, name_lookup)
            else:
                filename = INDEX_CSV_FILES.get(universe_name)
                if filename is None:
                    summary.append((universe_name, prev_count, prev_count, "skipped (unknown universe)"))
                    continue
                rows = _fetch_index_csv(session, filename)

            if not rows:
                raise ValueError("empty result set")

            for r in rows:
                name_lookup[r["symbol"]] = r

            if not dry_run:
                universes[universe_name] = rows
            summary.append((universe_name, prev_count, len(rows), "refreshed" if not dry_run else "dry-run ok"))
        except Exception as e:
            summary.append((universe_name, prev_count, prev_count, f"error: {e} (kept previous snapshot)"))

    if not dry_run:
        all_seen: dict[str, dict] = {}
        for entries in universes.values():
            for e in entries:
                all_seen[e["yf_ticker"]] = e
        universes["All Universe"] = sorted(all_seen.values(), key=lambda x: x["symbol"])

        out = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "NSE archives index CSVs (nsearchives.nseindia.com) + F&O market lots",
            "universes": universes,
        }
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"{'Universe':<25} {'Prev':>6} {'New':>6}  Status")
    print("-" * 70)
    for name, prev, new, status in summary:
        print(f"{name:<25} {prev:>6} {new:>6}  {status}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=str, default=None,
                         help="Comma-separated list of universe names to refresh")
    parser.add_argument("--dry-run", action="store_true",
                         help="Fetch and report counts without writing the snapshot file")
    args = parser.parse_args()
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    refresh(only, args.dry_run)


if __name__ == "__main__":
    main()
