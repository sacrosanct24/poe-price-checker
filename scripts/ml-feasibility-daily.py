#!/usr/bin/env python3
"""Generate a daily ML feasibility status report."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ListingStats:
    total: int
    affix_rows: int
    first_seen: Optional[str]
    last_seen: Optional[str]
    state_counts: List[Tuple[str, int]]
    base_counts: List[Tuple[str, int]]


@dataclass
class RunStats:
    total_runs: int
    last_started: Optional[str]
    last_completed: Optional[str]
    last_errors: Optional[int]


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None


def _format_duration(start: Optional[datetime], end: Optional[datetime]) -> str:
    if not start or not end:
        return "n/a"
    delta = end - start
    days = delta.total_seconds() / 86400
    return f"{delta} ({days:.2f} days)"


def _fetch_listing_stats(conn: sqlite3.Connection) -> ListingStats:
    total = conn.execute("SELECT COUNT(*) FROM ml_listings").fetchone()[0]
    affix_rows = conn.execute(
        "SELECT COUNT(*) FROM ml_listings WHERE affixes IS NOT NULL AND affixes != '[]'"
    ).fetchone()[0]
    first_seen, last_seen = conn.execute(
        "SELECT MIN(first_seen_at), MAX(last_seen_at) FROM ml_listings"
    ).fetchone()
    state_counts = conn.execute(
        "SELECT listing_state, COUNT(*) FROM ml_listings GROUP BY listing_state ORDER BY COUNT(*) DESC"
    ).fetchall()
    base_counts = conn.execute(
        "SELECT base_type, COUNT(*) FROM ml_listings GROUP BY base_type ORDER BY COUNT(*) DESC"
    ).fetchall()
    return ListingStats(
        total=total,
        affix_rows=affix_rows,
        first_seen=first_seen,
        last_seen=last_seen,
        state_counts=[(row[0], row[1]) for row in state_counts],
        base_counts=[(row[0], row[1]) for row in base_counts],
    )


def _fetch_run_stats(conn: sqlite3.Connection) -> RunStats:
    total_runs = conn.execute("SELECT COUNT(*) FROM ml_collection_runs").fetchone()[0]
    last = conn.execute(
        "SELECT started_at, completed_at, errors FROM ml_collection_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if last:
        return RunStats(
            total_runs=total_runs,
            last_started=last[0],
            last_completed=last[1],
            last_errors=last[2],
        )
    return RunStats(total_runs=total_runs, last_started=None, last_completed=None, last_errors=None)


def _fetch_mod_db_stats(mod_db_path: Path) -> Dict[str, Optional[str]]:
    if not mod_db_path.exists():
        return {"mod_count": None, "league": None, "last_update": None}

    conn = sqlite3.connect(mod_db_path)
    try:
        mod_count = conn.execute("SELECT COUNT(*) FROM mods").fetchone()[0]
        meta_rows = conn.execute("SELECT key, value FROM metadata").fetchall()
    finally:
        conn.close()

    metadata = {row[0]: row[1] for row in meta_rows}
    return {
        "mod_count": str(mod_count),
        "league": metadata.get("league"),
        "last_update": metadata.get("last_update"),
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report_dir = repo_root / "docs" / "ml_valuation" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    now_local = datetime.now().astimezone()
    date_stamp = now_local.strftime("%Y-%m-%d")
    report_path = report_dir / f"feasibility_status_{date_stamp}.md"

    db_path = Path.home() / ".poe_price_checker" / "data.db"
    mod_db_path = repo_root / "data" / "mods.db"

    if not db_path.exists():
        report_path.write_text(
            f"# ML Feasibility Daily Report\n\n"
            f"Date: {now_local.isoformat(timespec='seconds')}\n\n"
            "Status: BLOCKED (missing data.db)\n",
            encoding="utf-8",
        )
        return 0

    conn = sqlite3.connect(db_path)
    try:
        listing_stats = _fetch_listing_stats(conn)
        run_stats = _fetch_run_stats(conn)
    finally:
        conn.close()

    first_seen_dt = _parse_timestamp(listing_stats.first_seen)
    last_seen_dt = _parse_timestamp(listing_stats.last_seen)
    duration_text = _format_duration(first_seen_dt, last_seen_dt)
    duration_days = 0.0
    if first_seen_dt and last_seen_dt:
        duration_days = (last_seen_dt - first_seen_dt).total_seconds() / 86400

    mod_stats = _fetch_mod_db_stats(mod_db_path)
    mod_count = int(mod_stats["mod_count"]) if mod_stats["mod_count"] else 0

    coverage_ok = duration_days >= 14
    affix_ok = listing_stats.affix_rows > 0
    mods_ok = mod_count > 0

    if coverage_ok and affix_ok and mods_ok:
        gate_status = "READY (minimum coverage met; run full gate checks)"
    else:
        reasons = []
        if not coverage_ok:
            reasons.append("coverage < 14 days")
        if not affix_ok:
            reasons.append("no affix rows yet")
        if not mods_ok:
            reasons.append("mod database empty")
        gate_status = "BLOCKED (" + ", ".join(reasons) + ")"

    lines = [
        "# ML Feasibility Daily Report",
        "",
        f"Date: {now_local.isoformat(timespec='seconds')}",
        f"Status: {gate_status}",
        "",
        "## Collection Runs",
        "",
        f"- Total runs: {run_stats.total_runs}",
        f"- Last started: {run_stats.last_started or 'n/a'}",
        f"- Last completed: {run_stats.last_completed or 'n/a'}",
        f"- Last errors: {run_stats.last_errors if run_stats.last_errors is not None else 'n/a'}",
        "",
        "## Listings Coverage",
        "",
        f"- Total listings: {listing_stats.total}",
        f"- Listings with affixes: {listing_stats.affix_rows}",
        f"- First seen: {listing_stats.first_seen or 'n/a'}",
        f"- Last seen: {listing_stats.last_seen or 'n/a'}",
        f"- Coverage window: {duration_text}",
        "",
        "## Listing States",
        "",
        "| State | Count |",
        "| --- | --- |",
    ]

    for state, count in listing_stats.state_counts:
        lines.append(f"| {state} | {count} |")

    lines.extend(
        [
            "",
            "## Base Types",
            "",
            "| Base type | Count |",
            "| --- | --- |",
        ]
    )
    for base, count in listing_stats.base_counts:
        lines.append(f"| {base} | {count} |")

    lines.extend(
        [
            "",
            "## Mod Database",
            "",
            f"- Mod count: {mod_stats['mod_count'] or 'n/a'}",
            f"- League: {mod_stats['league'] or 'n/a'}",
            f"- Last update: {mod_stats['last_update'] or 'n/a'}",
            "",
        ]
    )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
