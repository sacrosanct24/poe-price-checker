#!/usr/bin/env python3
"""
Economy Snapshot Collection Script.

Fetches current economy data from poe.ninja and stores it locally.
Can be run manually or scheduled (e.g., daily cron job).

Usage:
    python scripts/collect_economy_snapshot.py [--leagues LEAGUE1,LEAGUE2]

Examples:
    python scripts/collect_economy_snapshot.py
    python scripts/collect_economy_snapshot.py --leagues Keepers,Standard
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import Database
from core.league_economy_history import LeagueEconomyService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default leagues to track
DEFAULT_LEAGUES = ["Keepers", "Standard"]


def collect_snapshots(leagues: list[str] | None = None) -> dict[str, bool]:
    """
    Collect economy snapshots for specified leagues.

    Args:
        leagues: List of league names, or None for defaults

    Returns:
        Dict of league -> success status
    """
    if leagues is None:
        leagues = DEFAULT_LEAGUES

    # Initialize database
    db_path = Path.home() / ".poe_price_checker" / "data.db"
    db = Database(db_path)
    service = LeagueEconomyService(db)

    results = {}
    logger.info(f"Collecting economy snapshots for {len(leagues)} league(s)...")

    for league in leagues:
        logger.info(f"Fetching {league}...")
        try:
            snapshot = service.fetch_and_store_snapshot(league)
            if snapshot:
                logger.info(
                    f"  {league}: Divine={snapshot.divine_to_chaos:.0f}c, "
                    f"Top={snapshot.top_uniques[0].item_name if snapshot.top_uniques else 'N/A'}"
                )
                results[league] = True
            else:
                logger.warning(f"  {league}: No data available")
                results[league] = False
        except Exception as e:
            logger.error(f"  {league}: Error - {e}")
            results[league] = False

    db.close()

    # Summary
    success = sum(1 for v in results.values() if v)
    logger.info(f"Done: {success}/{len(leagues)} leagues collected successfully")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Collect PoE economy snapshots from poe.ninja"
    )
    parser.add_argument(
        "--leagues",
        type=str,
        help=f"Comma-separated list of leagues (default: {','.join(DEFAULT_LEAGUES)})",
    )

    args = parser.parse_args()

    leagues = None
    if args.leagues:
        leagues = [l.strip() for l in args.leagues.split(",")]

    results = collect_snapshots(leagues)

    # Exit with error if any failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
