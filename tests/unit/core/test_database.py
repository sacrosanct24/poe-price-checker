from __future__ import annotations

import time
from datetime import datetime, timedelta
import pytest

from core.database import Database
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


# -------------------------
# Fixtures
# -------------------------

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    return Database(db_path)


# -------------------------
# Checked Items
# -------------------------

def test_get_checked_items_returns_newest_first(temp_db):
    temp_db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Test",
        item_name="First",
        chaos_value=100.0,
    )
    time.sleep(0.01)
    temp_db.add_checked_item(
        game_version=GameVersion.POE1,
        league="Test",
        item_name="Second",
        chaos_value=200.0,
    )

    items = temp_db.get_checked_items(limit=10)

    assert len(items) >= 2
    assert items[0]["item_name"] == "Second"
    assert items[1]["item_name"] == "First"


def test_get_checked_items_filters_by_game_and_league(temp_db):
    temp_db.add_checked_item(
        GameVersion.POE1,
        "Standard",
        "Item A",
        chaos_value=10.0,
    )
    temp_db.add_checked_item(
        GameVersion.POE2,
        "Hardcore",
        "Item B",
        chaos_value=20.0,
    )

    result = temp_db.get_checked_items(
        game_version=GameVersion.POE1,
        league="Standard",
    )

    assert len(result) == 1
    assert result[0]["item_name"] == "Item A"


# -------------------------
# Sales
# -------------------------

def test_complete_sale(temp_db):
    sale_id = temp_db.add_sale(
        item_name="Item X",
        listed_price_chaos=100.0,
    )

    time.sleep(0.1)
    now = datetime.now()
    temp_db.complete_sale(
        sale_id,
        actual_price_chaos=95.0,
        sold_at=now,
    )

    sales = temp_db.get_sales(sold_only=True)
    assert len(sales) == 1

    sale = sales[0]
    assert sale["id"] == sale_id
    assert sale["actual_price_chaos"] == 95.0
    assert sale["sold_at"] is not None
    assert sale["time_to_sale_hours"] >= 0
    assert sale["time_to_sale_hours"] < 1.0


def test_get_sales_filters_sold_only(temp_db):
    s1 = temp_db.add_sale("Item A", listed_price_chaos=10.0)
    s2 = temp_db.add_sale("Item B", listed_price_chaos=20.0)

    temp_db.complete_sale(s2, actual_price_chaos=19.0, sold_at=datetime.now())

    all_sales = temp_db.get_sales(sold_only=False)
    sold_sales = temp_db.get_sales(sold_only=True)

    ids_all = {s["id"] for s in all_sales}
    ids_sold = {s["id"] for s in sold_sales}

    assert s1 in ids_all and s2 in ids_all
    assert s2 in ids_sold
    assert s1 not in ids_sold


def test_mark_sale_unsold_sets_notes_and_sold_at(temp_db):
    sale_id = temp_db.add_sale("Item A", listed_price_chaos=10.0)
    temp_db.complete_sale(sale_id, actual_price_chaos=9.0, sold_at=datetime.now())

    temp_db.mark_sale_unsold(sale_id)

    sales = temp_db.get_sales()
    sale = next(s for s in sales if s["id"] == sale_id)

    assert sale["notes"] == "Did not sell"
    assert sale["sold_at"] is not None


def test_record_instant_sale_inserts_row(temp_db):
    sale_id = temp_db.record_instant_sale(
        item_name="Monkey Sword",
        chaos_value=123.0,
        item_base_type="Fancy Base",
        notes="Testing",
    )

    rows = temp_db.conn.execute("SELECT * FROM sales").fetchall()
    assert len(rows) == 1
    row = rows[0]

    assert row["id"] == sale_id
    assert row["item_name"] == "Monkey Sword"
    assert row["item_base_type"] == "Fancy Base"
    assert row["notes"] == "Testing"
    assert row["listed_price_chaos"] == 123.0
    assert row["actual_price_chaos"] == 123.0

    listed_at = datetime.fromisoformat(row["listed_at"])
    sold_at = datetime.fromisoformat(row["sold_at"])
    assert abs((sold_at - listed_at).total_seconds()) < 2.0
    assert row["time_to_sale_hours"] == 0.0


def test_record_instant_sale_updates_stats_counts(temp_db):
    before = temp_db.get_stats()

    assert before["checked_items"] == 0
    assert before["sales"] == 0
    assert before["completed_sales"] == 0
    assert before["price_snapshots"] == 0

    temp_db.record_instant_sale(
        item_name="Instant Sale",
        chaos_value=50.0,
        item_base_type="Base",
        notes="Testing",
    )

    after = temp_db.get_stats()

    assert after["checked_items"] == before["checked_items"] == 0
    assert after["price_snapshots"] == before["price_snapshots"] == 0
    assert after["sales"] == before["sales"] + 1
    assert after["completed_sales"] == before["completed_sales"] + 1


# -------------------------
# Plugin State
# -------------------------

def test_db_plugin_state_roundtrip(temp_db):
    temp_db.set_plugin_enabled("price_alert", True)
    temp_db.set_plugin_config("price_alert", '{"threshold": 100}')

    assert temp_db.is_plugin_enabled("price_alert") is True
    assert temp_db.get_plugin_config("price_alert") == '{"threshold": 100}'

    temp_db.set_plugin_enabled("price_alert", False)
    assert temp_db.is_plugin_enabled("price_alert") is False


# -------------------------
# Price History
# -------------------------

def test_price_history_respects_days_parameter(temp_db):
    item_name = "Divine Orb"

    temp_db.add_price_snapshot(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name=item_name,
        chaos_value=300.0,
    )

    old_date = (datetime.now() - timedelta(days=10)).isoformat()
    temp_db.conn.execute(
        """
        INSERT INTO price_history
        (game_version, league, item_name, chaos_value, recorded_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (GameVersion.POE1.value, "Standard", item_name, 250.0, old_date),
    )
    temp_db.conn.commit()

    last_7_days = temp_db.get_price_history(
        item_name, GameVersion.POE1, "Standard", days=7
    )
    assert len(last_7_days) == 1
    assert last_7_days[0]["chaos_value"] == 300.0

    last_30_days = temp_db.get_price_history(
        item_name, GameVersion.POE1, "Standard", days=30
    )
    assert len(last_30_days) == 2


def test_price_history_ordered_by_date_ascending(temp_db):
    item_name = "Exalted Orb"
    base = datetime.now()

    data = [
        (290.0, base - timedelta(hours=4)),
        (295.0, base - timedelta(hours=3)),
        (300.0, base - timedelta(hours=2)),
        (305.0, base - timedelta(hours=1)),
        (310.0, base),
    ]

    for price, ts in data:
        temp_db.conn.execute(
            """
            INSERT INTO price_history
            (game_version, league, item_name, chaos_value, recorded_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (GameVersion.POE1.value, "Standard", item_name, price, ts.isoformat()),
        )
    temp_db.conn.commit()

    hist = temp_db.get_price_history(
        item_name, GameVersion.POE1, "Standard", days=7
    )

    assert len(hist) == 5
    vals = [h["chaos_value"] for h in hist]
    assert vals == [290.0, 295.0, 300.0, 305.0, 310.0]


# -------------------------
# Stats Summary
# -------------------------

def test_get_stats_counts_are_consistent(temp_db):
    temp_db.add_checked_item(GameVersion.POE1, "Standard", "Item A", chaos_value=1.0)
    temp_db.add_checked_item(GameVersion.POE1, "Standard", "Item B", chaos_value=2.0)

    s = temp_db.add_sale("Item A", listed_price_chaos=1.0)
    temp_db.complete_sale(s, actual_price_chaos=1.0, sold_at=datetime.now())

    for val in (10.0, 20.0, 30.0):
        temp_db.add_price_snapshot(
            game_version=GameVersion.POE1,
            league="Standard",
            item_name="Item A",
            chaos_value=val,
        )

    stats = temp_db.get_stats()
    assert stats["checked_items"] == 2
    assert stats["sales"] == 1
    assert stats["completed_sales"] == 1
    assert stats["price_snapshots"] == 3
