# tests/test_database_fixes.py
"""
Fixes for database test failures.
These patches should be applied to test_database.py
"""

import time
from datetime import datetime, timedelta
import pytest
from core.database import Database
from core.game_version import GameVersion


# Fix for: test_get_checked_items_returns_newest_first
def test_get_checked_items_returns_newest_first_FIXED(temp_db):
    """Items should be returned with newest first"""
    # Add items with explicit timing to ensure ordering
    temp_db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Test",
        item_name="First",
        chaos_value=100.0
    )

    # Sleep to ensure different timestamps
    time.sleep(0.01)

    temp_db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Test",
        item_name="Second",
        chaos_value=200.0
    )

    items = temp_db.get_checked_items(limit=10)

    # Newest (Second) should be first in the list
    assert len(items) >= 2
    assert items[0]['item_name'] == "Second"
    assert items[1]['item_name'] == "First"


# Fix for: test_complete_sale_updates_fields and test_complete_sale_calculates_time_to_sale
def test_complete_sale_FIXED(temp_db):
    """Test sale completion with proper timing"""
    # Create sale with known time
    sale_id = temp_db.add_sale(
        item_name="Test Item",
        listed_price_chaos=100.0
    )

    # Wait a bit to ensure time passes
    time.sleep(0.1)

    # Complete the sale
    sold_time = datetime.now()
    temp_db.complete_sale(sale_id, actual_price_chaos=95.0, sold_at=sold_time)

    # Retrieve the sale
    sales = temp_db.get_sales(sold_only=True)
    assert len(sales) == 1

    sale = sales[0]
    assert sale['id'] == sale_id
    assert sale['actual_price_chaos'] == 95.0
    assert sale['sold_at'] is not None

    # Time to sale should be positive and reasonable (< 1 hour for this test)
    assert sale['time_to_sale_hours'] is not None
    assert sale['time_to_sale_hours'] >= 0
    assert sale['time_to_sale_hours'] < 1.0  # Should be just a fraction of a second


# Fix for: test_get_price_history_respects_days_parameter
def test_get_price_history_respects_days_parameter_FIXED(temp_db):
    """Price history should respect the days filter"""
    item_name = "Divine Orb"

    # Add recent snapshot (within 7 days)
    temp_db.add_price_snapshot(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name=item_name,
        chaos_value=300.0
    )

    # Add old snapshot by manipulating the database directly
    # (since add_price_snapshot uses CURRENT_TIMESTAMP)
    import sqlite3
    old_date = (datetime.now() - timedelta(days=10)).isoformat()

    temp_db.conn.execute("""
                         INSERT INTO price_history
                             (game_version, league, item_name, chaos_value, recorded_at)
                         VALUES (?, ?, ?, ?, ?)
                         """, (GameVersion.POE1.value, "Standard", item_name, 250.0, old_date))
    temp_db.conn.commit()

    # Get last 7 days
    history_7d = temp_db.get_price_history(
        item_name=item_name,
        game_version=GameVersion.POE1,
        league="Standard",
        days=7
    )

    # Should only get the recent one
    assert len(history_7d) == 1
    assert history_7d[0]['chaos_value'] == 300.0

    # Get last 30 days
    history_30d = temp_db.get_price_history(
        item_name=item_name,
        game_version=GameVersion.POE1,
        league="Standard",
        days=30
    )

    # Should get both
    assert len(history_30d) == 2


# Fix for: test_price_history_ordered_by_date_ascending
def test_price_history_ordered_by_date_ascending_FIXED(temp_db):
    """Price history should be ordered oldest to newest"""
    item_name = "Exalted Orb"

    # We need to insert with specific timestamps
    # Since add_price_snapshot uses CURRENT_TIMESTAMP, we'll insert directly
    import sqlite3

    base_time = datetime.now()
    prices_and_times = [
        (290.0, base_time - timedelta(hours=4)),
        (295.0, base_time - timedelta(hours=3)),
        (300.0, base_time - timedelta(hours=2)),
        (305.0, base_time - timedelta(hours=1)),
        (310.0, base_time),
    ]

    for price, timestamp in prices_and_times:
        temp_db.conn.execute("""
                             INSERT INTO price_history
                                 (game_version, league, item_name, chaos_value, recorded_at)
                             VALUES (?, ?, ?, ?, ?)
                             """, (GameVersion.POE1.value, "Standard", item_name, price, timestamp.isoformat()))

    temp_db.conn.commit()

    # Get history
    history = temp_db.get_price_history(
        item_name=item_name,
        game_version=GameVersion.POE1,
        league="Standard",
        days=7
    )

    # Should be ordered oldest to newest (ascending)
    assert len(history) == 5
    values = [h['chaos_value'] for h in history]
    assert values == [290.0, 295.0, 300.0, 305.0, 310.0]

def test_get_sales_filters_sold_only(temp_db):
    # Unsold sale
    sale1 = temp_db.add_sale(item_name="Item A", listed_price_chaos=10.0)

    # Sold sale
    sale2 = temp_db.add_sale(item_name="Item B", listed_price_chaos=20.0)
    temp_db.complete_sale(sale2, actual_price_chaos=19.0, sold_at=datetime.now())

    all_sales = temp_db.get_sales(sold_only=False)
    sold_sales = temp_db.get_sales(sold_only=True)

    ids_all = {s["id"] for s in all_sales}
    ids_sold = {s["id"] for s in sold_sales}

    assert sale1 in ids_all and sale2 in ids_all
    assert sale2 in ids_sold
    assert sale1 not in ids_sold

def test_mark_sale_unsold_sets_notes_and_sold_at(temp_db):
    sale_id = temp_db.add_sale(item_name="Item A", listed_price_chaos=10.0)
    temp_db.complete_sale(sale_id, actual_price_chaos=9.0, sold_at=datetime.now())

    temp_db.mark_sale_unsold(sale_id)

    sales = temp_db.get_sales()
    sale = next(s for s in sales if s["id"] == sale_id)

    assert sale["notes"] == "Did not sell"
    assert sale["sold_at"] is not None
    # We do NOT assert anything about time_to_sale_hours here; current code doesn’t change it.

def test_db_plugin_state_roundtrip(temp_db):
    temp_db.set_plugin_enabled("price_alert", True)
    temp_db.set_plugin_config("price_alert", '{"threshold": 100}')

    assert temp_db.is_plugin_enabled("price_alert") is True
    assert temp_db.get_plugin_config("price_alert") == '{"threshold": 100}'

    # Disable and ensure it flips
    temp_db.set_plugin_enabled("price_alert", False)
    assert temp_db.is_plugin_enabled("price_alert") is False

def test_get_checked_items_filters_by_game_and_league(temp_db):
    # PoE1 / Standard
    temp_db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Item A",
        chaos_value=10.0,
    )

    # PoE2 / Hardcore
    temp_db.add_checked_item(
        game_version=GameVersion.POE2,
        league="Hardcore",
        item_name="Item B",
        chaos_value=20.0,
    )

    poe1_items = temp_db.get_checked_items(game_version=GameVersion.POE1, league="Standard")
    assert len(poe1_items) == 1
    assert poe1_items[0]["item_name"] == "Item A"

def test_get_stats_counts_are_consistent(temp_db):
    # 2 checked items
    temp_db.add_checked_item(GameVersion.POE1, "Standard", "Item A", chaos_value=1.0)
    temp_db.add_checked_item(GameVersion.POE1, "Standard", "Item B", chaos_value=2.0)

    # 1 completed sale
    sale_id = temp_db.add_sale("Item A", listed_price_chaos=1.0)
    temp_db.complete_sale(sale_id, actual_price_chaos=1.0, sold_at=datetime.now())

    # 3 price snapshots
    for v in (10.0, 20.0, 30.0):
        temp_db.add_price_snapshot(
            game_version=GameVersion.POE1,
            league="Standard",
            item_name="Item A",
            chaos_value=v,
        )

    stats = temp_db.get_stats()
    assert stats["checked_items"] == 2
    assert stats["sales"] == 1
    assert stats["completed_sales"] == 1
    assert stats["price_snapshots"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])