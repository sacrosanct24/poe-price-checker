"""
Command-line interface for price rankings.

Provides print utilities and CLI entry point.
"""
from __future__ import annotations

import argparse
import logging
from typing import Any, Dict, List

from core.rankings.models import CategoryRanking
from core.rankings.constants import CACHE_EXPIRY_DAYS
from core.rankings.cache import PriceRankingCache
from core.rankings.calculator import Top20Calculator
from core.rankings.history import PriceRankingHistory


def print_ranking(ranking: CategoryRanking, limit: int = 20, show_divine: bool = True) -> None:
    """Pretty-print a category ranking."""
    print(f"\n{'='*60}")
    print(f" {ranking.display_name}")
    print(f"{'='*60}")

    for item in ranking.items[:limit]:
        divine_str = ""
        if show_divine and item.divine_value:
            divine_str = f" ({item.divine_value:.2f} div)"

        base_str = ""
        if item.base_type:
            base_str = f" [{item.base_type}]"

        print(f"  {item.rank:2}. {item.name}{base_str}: {item.chaos_value:,.0f}c{divine_str}")


def print_trending(trending: List[Dict[str, Any]], category: str) -> None:
    """Pretty-print trending items."""
    print(f"\n{'='*60}")
    print(f" Trending: {category}")
    print(f"{'='*60}")

    if not trending:
        print("  No significant price changes found.")
        return

    for item in trending:
        arrow = "↑" if item["trend"] == "up" else "↓"
        # Could add ANSI colors here
        print(f"  {arrow} {item['name']}: {item['old_price']:,.0f}c → {item['new_price']:,.0f}c ({item['change_percent']:+.1f}%)")


def cli_main() -> None:
    """Command-line interface for price rankings."""
    parser = argparse.ArgumentParser(
        description="PoE Price Rankings - View top 20 items by category",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m core.price_rankings                    # Show all categories
  python -m core.price_rankings -c currency        # Show currency only
  python -m core.price_rankings -g uniques         # Show all unique categories
  python -m core.price_rankings -s helmet          # Show top 20 unique helmets
  python -m core.price_rankings -s body_armour    # Show top 20 unique body armours
  python -m core.price_rankings --slots            # Show all equipment slots
  python -m core.price_rankings --refresh          # Force refresh from API
  python -m core.price_rankings --trending         # Show trending items
  python -m core.price_rankings --history "Divine Orb"  # Show item history
        """
    )

    parser.add_argument("-l", "--league", help="League name (auto-detects current temp league)")
    parser.add_argument("-c", "--category", help="Specific category to show",
                       choices=list(PriceRankingCache.CATEGORIES.keys()))
    parser.add_argument("-s", "--slot", help="Equipment slot to show (e.g., helmet, body_armour, sword)",
                       choices=list(PriceRankingCache.EQUIPMENT_SLOTS.keys()))
    parser.add_argument("--slots", action="store_true", help="Show all equipment slot rankings")
    parser.add_argument("-g", "--group", help="Category group",
                       choices=["uniques", "consumables", "cards", "all"])
    parser.add_argument("-n", "--limit", type=int, default=20, help="Number of items to show (default: 20)")
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--save", action="store_true", help="Save snapshot to database")
    parser.add_argument("--trending", action="store_true", help="Show trending items (price changes)")
    parser.add_argument("--history", metavar="ITEM", help="Show price history for an item")
    parser.add_argument("--days", type=int, default=7, help="Days for trending/history (default: 7)")
    parser.add_argument("--list-categories", action="store_true", help="List available categories")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress info messages")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s")

    # List categories and exit
    if args.list_categories:
        print("\nAvailable categories:")
        for key, name in PriceRankingCache.CATEGORIES.items():
            print(f"  {key:20} - {name}")
        print("\nCategory groups:")
        print("  uniques     - All unique item categories")
        print("  consumables - Currency, fragments, scarabs, etc.")
        print("  cards       - Divination cards")
        print("  all         - All categories")
        print("\nEquipment slots (for unique items):")
        for key, name in PriceRankingCache.SLOT_DISPLAY_NAMES.items():
            print(f"  {key:20} - {name}")
        return

    # Detect league
    if args.league:
        league = args.league
    else:
        from data_sources.pricing.poe_ninja import PoeNinjaAPI
        api = PoeNinjaAPI()
        league = api.detect_current_league()
        print(f"Using league: {league}")

    # Initialize cache
    cache = PriceRankingCache(league=league)
    calculator = Top20Calculator(cache)

    # Handle item history
    if args.history:
        with PriceRankingHistory() as history_db:
            history = history_db.get_item_history(args.history, league, days=args.days, category=args.category)

            print(f"\n{'='*60}")
            print(f" Price History: {args.history}")
            print(f"{'='*60}")

            if not history:
                print("  No history found. Run with --save to store snapshots.")
            else:
                for entry in history:
                    divine_str = f" ({entry['divine_value']:.2f} div)" if entry.get('divine_value') else ""
                    print(f"  {entry['snapshot_date']}: #{entry['rank']} - {entry['chaos_value']:,.0f}c{divine_str}")
        return

    # Handle trending
    if args.trending:
        # Import here to avoid circular imports
        from core.rankings import get_rankings_by_group

        # Need to refresh first to ensure we have current data
        rankings = calculator.refresh_all(force=args.refresh)

        with PriceRankingHistory() as history_db:
            # Save current snapshot
            if args.save or True:  # Always save for trending
                history_db.save_all_snapshots(rankings, league)

            categories_to_check = [args.category] if args.category else list(PriceRankingCache.CATEGORIES.keys())

            for cat in categories_to_check:
                trending = history_db.get_trending_items(league, cat, days=args.days)
                if trending:
                    print_trending(trending, PriceRankingCache.CATEGORIES.get(cat, cat))
        return

    # Fetch rankings
    if args.slot:
        # Single equipment slot
        ranking = calculator.refresh_slot(args.slot, force=args.refresh)
        if ranking:
            print_ranking(ranking, limit=args.limit)
            if args.save:
                with PriceRankingHistory() as history_db:
                    history_db.save_snapshot(ranking, league)
                print("\nSnapshot saved to database.")
    elif args.slots:
        # All equipment slots
        rankings = calculator.refresh_all_slots(force=args.refresh)
        for ranking in rankings.values():
            print_ranking(ranking, limit=args.limit)
        if args.save:
            with PriceRankingHistory() as history_db:
                history_db.save_all_snapshots(rankings, league)
            print("\nSnapshots saved to database.")
    elif args.category:
        ranking = calculator.refresh_category(args.category, force=args.refresh)
        if ranking:
            print_ranking(ranking, limit=args.limit)
            if args.save:
                with PriceRankingHistory() as history_db:
                    history_db.save_snapshot(ranking, league)
                print("\nSnapshot saved to database.")
    elif args.group:
        # Import here to avoid circular imports
        from core.rankings import get_rankings_by_group

        rankings = get_rankings_by_group(args.group, league=league, force_refresh=args.refresh)
        for ranking in rankings.values():
            print_ranking(ranking, limit=args.limit)
        if args.save:
            with PriceRankingHistory() as history_db:
                history_db.save_all_snapshots(rankings, league)
            print("\nSnapshots saved to database.")
    else:
        rankings = calculator.refresh_all(force=args.refresh)
        for ranking in rankings.values():
            print_ranking(ranking, limit=args.limit)
        if args.save:
            with PriceRankingHistory() as history_db:
                history_db.save_all_snapshots(rankings, league)
            print("\nSnapshots saved to database.")

    # Show cache status
    age = cache.get_cache_age_days()
    if age is not None:
        print(f"\nCache age: {age:.1f} days (refreshes after {CACHE_EXPIRY_DAYS} days)")
