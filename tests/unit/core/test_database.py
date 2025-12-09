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
        GameVersion.POE1, "Standard", item_name, days=7
    )
    assert len(last_7_days) == 1
    assert last_7_days[0]["chaos_value"] == 300.0

    last_30_days = temp_db.get_price_history(
        GameVersion.POE1, "Standard", item_name, days=30
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
        GameVersion.POE1, "Standard", item_name, days=7
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


# -------------------------
# Upgrade Advice History
# -------------------------

def test_save_upgrade_advice_history_inserts_entry(temp_db):
    """Test saving upgrade advice creates a new entry."""
    temp_db.save_upgrade_advice_history(
        profile_name="TestBuild",
        slot="Helmet",
        item_hash="abc123",
        advice_text="# Analysis\n\nThis is the advice.",
        ai_model="gemini-2.0-flash",
        ai_provider="gemini",
        include_stash=True,
        stash_candidates_count=5,
    )

    history = temp_db.get_upgrade_advice_history("TestBuild", "Helmet")
    assert len(history) == 1
    # profile_name and slot are not in returned dict (they're query params)
    assert history[0]["item_hash"] == "abc123"
    assert history[0]["advice_text"] == "# Analysis\n\nThis is the advice."
    assert history[0]["ai_provider"] == "gemini"
    assert history[0]["include_stash"] == 1  # SQLite stores as 1/0
    assert history[0]["stash_candidates_count"] == 5


def test_upgrade_advice_history_returns_newest_first(temp_db):
    """Test history is returned with newest entries first."""
    for i in range(3):
        time.sleep(0.01)  # Ensure different timestamps
        temp_db.save_upgrade_advice_history(
            profile_name="TestBuild",
            slot="Helmet",
            item_hash=f"hash{i}",
            advice_text=f"Advice {i}",
            ai_provider="gemini",
            include_stash=False,
        )

    history = temp_db.get_upgrade_advice_history("TestBuild", "Helmet")
    assert len(history) == 3
    # Newest first (hash2, hash1, hash0)
    assert history[0]["item_hash"] == "hash2"
    assert history[1]["item_hash"] == "hash1"
    assert history[2]["item_hash"] == "hash0"


def test_upgrade_advice_history_limits_to_5_entries(temp_db):
    """Test that only the last 5 entries are kept per slot."""
    for i in range(7):
        time.sleep(0.01)  # Ensure different timestamps
        temp_db.save_upgrade_advice_history(
            profile_name="TestBuild",
            slot="Helmet",
            item_hash=f"hash{i}",
            advice_text=f"Advice {i}",
            ai_provider="gemini",
            include_stash=False,
        )

    history = temp_db.get_upgrade_advice_history("TestBuild", "Helmet")
    assert len(history) == 5
    # Should have hash6, hash5, hash4, hash3, hash2 (newest 5)
    hashes = [h["item_hash"] for h in history]
    assert "hash0" not in hashes
    assert "hash1" not in hashes
    assert "hash6" in hashes


def test_upgrade_advice_history_separate_by_profile(temp_db):
    """Test that history is separate per profile."""
    temp_db.save_upgrade_advice_history(
        profile_name="Build1",
        slot="Helmet",
        item_hash="hash1",
        advice_text="Advice for Build1",
        include_stash=False,
    )
    temp_db.save_upgrade_advice_history(
        profile_name="Build2",
        slot="Helmet",
        item_hash="hash2",
        advice_text="Advice for Build2",
        include_stash=False,
    )

    history1 = temp_db.get_upgrade_advice_history("Build1", "Helmet")
    history2 = temp_db.get_upgrade_advice_history("Build2", "Helmet")

    assert len(history1) == 1
    assert len(history2) == 1
    assert history1[0]["advice_text"] == "Advice for Build1"
    assert history2[0]["advice_text"] == "Advice for Build2"


def test_upgrade_advice_history_separate_by_slot(temp_db):
    """Test that history is separate per equipment slot."""
    temp_db.save_upgrade_advice_history(
        profile_name="TestBuild",
        slot="Helmet",
        item_hash="hash1",
        advice_text="Helmet advice",
        include_stash=False,
    )
    temp_db.save_upgrade_advice_history(
        profile_name="TestBuild",
        slot="Gloves",
        item_hash="hash2",
        advice_text="Gloves advice",
        include_stash=False,
    )

    helmet_history = temp_db.get_upgrade_advice_history("TestBuild", "Helmet")
    gloves_history = temp_db.get_upgrade_advice_history("TestBuild", "Gloves")

    assert len(helmet_history) == 1
    assert len(gloves_history) == 1
    # Verify they are separate by checking the advice text (slot is query param)
    assert helmet_history[0]["advice_text"] == "Helmet advice"
    assert gloves_history[0]["advice_text"] == "Gloves advice"


def test_get_latest_advice_from_history(temp_db):
    """Test getting the most recent advice."""
    temp_db.save_upgrade_advice_history(
        profile_name="TestBuild",
        slot="Helmet",
        item_hash="old_hash",
        advice_text="Old advice",
        include_stash=False,
    )
    time.sleep(0.01)
    temp_db.save_upgrade_advice_history(
        profile_name="TestBuild",
        slot="Helmet",
        item_hash="new_hash",
        advice_text="New advice",
        include_stash=False,
    )

    latest = temp_db.get_latest_advice_from_history("TestBuild", "Helmet")
    assert latest is not None
    assert latest["item_hash"] == "new_hash"
    assert latest["advice_text"] == "New advice"


def test_get_latest_advice_from_history_nonexistent(temp_db):
    """Test getting latest advice when none exists."""
    latest = temp_db.get_latest_advice_from_history("NonExistent", "Helmet")
    assert latest is None


def test_get_all_slots_latest_history(temp_db):
    """Test getting latest history for all slots at once."""
    slots = ["Helmet", "Gloves", "Boots"]
    for slot in slots:
        temp_db.save_upgrade_advice_history(
            profile_name="TestBuild",
            slot=slot,
            item_hash=f"hash_{slot}",
            advice_text=f"Advice for {slot}",
            include_stash=False,
        )

    all_latest = temp_db.get_all_slots_latest_history("TestBuild")

    assert len(all_latest) == 3
    assert "Helmet" in all_latest
    assert "Gloves" in all_latest
    assert "Boots" in all_latest
    assert all_latest["Helmet"]["item_hash"] == "hash_Helmet"


def test_clear_upgrade_advice_history(temp_db):
    """Test clearing history for a profile/slot."""
    temp_db.save_upgrade_advice_history(
        profile_name="TestBuild",
        slot="Helmet",
        item_hash="hash1",
        advice_text="Advice 1",
        include_stash=False,
    )
    temp_db.save_upgrade_advice_history(
        profile_name="TestBuild",
        slot="Helmet",
        item_hash="hash2",
        advice_text="Advice 2",
        include_stash=False,
    )

    # Should have 2 entries
    assert len(temp_db.get_upgrade_advice_history("TestBuild", "Helmet")) == 2

    # Clear them
    temp_db.clear_upgrade_advice_history("TestBuild", "Helmet")

    # Should have 0 entries
    assert len(temp_db.get_upgrade_advice_history("TestBuild", "Helmet")) == 0


# -------------------------
# Verdict Statistics (v11+)
# -------------------------

def test_save_verdict_statistics_creates_entry(temp_db):
    """Test saving verdict statistics creates a new entry."""
    stats = {
        "keep_count": 5,
        "vendor_count": 10,
        "maybe_count": 3,
        "keep_value": 250.5,
        "vendor_value": 15.0,
        "maybe_value": 50.0,
        "items_with_meta_bonus": 2,
        "total_meta_bonus": 30.0,
        "high_confidence_count": 8,
        "medium_confidence_count": 7,
        "low_confidence_count": 3,
    }

    temp_db.save_verdict_statistics(
        league="TestLeague",
        game_version="poe1",
        session_date="2025-01-15",
        stats=stats,
    )

    result = temp_db.get_verdict_statistics(
        league="TestLeague",
        game_version="poe1",
        session_date="2025-01-15",
    )

    assert result is not None
    assert result["keep_count"] == 5
    assert result["vendor_count"] == 10
    assert result["maybe_count"] == 3
    assert result["keep_value"] == 250.5
    assert result["items_with_meta_bonus"] == 2


def test_save_verdict_statistics_upserts(temp_db):
    """Test saving verdict statistics updates existing entry."""
    stats1 = {"keep_count": 5, "vendor_count": 10, "maybe_count": 3}
    stats2 = {"keep_count": 15, "vendor_count": 20, "maybe_count": 8}

    temp_db.save_verdict_statistics(
        league="TestLeague",
        game_version="poe1",
        session_date="2025-01-15",
        stats=stats1,
    )

    # Save again with updated stats
    temp_db.save_verdict_statistics(
        league="TestLeague",
        game_version="poe1",
        session_date="2025-01-15",
        stats=stats2,
    )

    result = temp_db.get_verdict_statistics(
        league="TestLeague",
        game_version="poe1",
        session_date="2025-01-15",
    )

    # Should have the updated values
    assert result["keep_count"] == 15
    assert result["vendor_count"] == 20
    assert result["maybe_count"] == 8


def test_get_verdict_statistics_returns_none_if_not_found(temp_db):
    """Test getting verdict statistics returns None when not found."""
    result = temp_db.get_verdict_statistics(
        league="NonExistent",
        game_version="poe1",
        session_date="2025-01-15",
    )

    assert result is None


def test_get_verdict_statistics_filters_by_league(temp_db):
    """Test getting verdict statistics filters by league correctly."""
    temp_db.save_verdict_statistics(
        league="League1",
        game_version="poe1",
        session_date="2025-01-15",
        stats={"keep_count": 5},
    )
    temp_db.save_verdict_statistics(
        league="League2",
        game_version="poe1",
        session_date="2025-01-15",
        stats={"keep_count": 10},
    )

    result = temp_db.get_verdict_statistics(
        league="League1",
        game_version="poe1",
        session_date="2025-01-15",
    )

    assert result is not None
    assert result["keep_count"] == 5


def test_get_verdict_statistics_history(temp_db):
    """Test getting verdict statistics history."""
    from datetime import datetime, timedelta

    # Create stats for recent dates (relative to today)
    today = datetime.now()
    dates = [
        (today - timedelta(days=2)).strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
    ]

    for i, date in enumerate(dates):
        temp_db.save_verdict_statistics(
            league="TestLeague",
            game_version="poe1",
            session_date=date,
            stats={"keep_count": i + 1},
        )

    history = temp_db.get_verdict_statistics_history(
        league="TestLeague",
        game_version="poe1",
        days=30,
    )

    assert len(history) == 3
    # Newest first (today's date)
    assert history[0]["session_date"] == dates[2]
    assert history[0]["keep_count"] == 3


def test_get_verdict_statistics_summary(temp_db):
    """Test getting aggregated verdict statistics summary."""
    from datetime import datetime, timedelta

    # Use recent dates relative to today
    today = datetime.now()
    dates = [
        (today - timedelta(days=2)).strftime("%Y-%m-%d"),
        (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
    ]

    for date in dates:
        temp_db.save_verdict_statistics(
            league="TestLeague",
            game_version="poe1",
            session_date=date,
            stats={"keep_count": 10, "vendor_count": 5, "keep_value": 100.0},
        )

    summary = temp_db.get_verdict_statistics_summary(
        league="TestLeague",
        game_version="poe1",
    )

    assert summary["session_count"] == 3
    assert summary["total_keep"] == 30  # 10 * 3
    assert summary["total_vendor"] == 15  # 5 * 3
    assert summary["total_keep_value"] == 300.0  # 100 * 3


def test_clear_verdict_statistics_all(temp_db):
    """Test clearing all verdict statistics."""
    temp_db.save_verdict_statistics(
        league="League1",
        game_version="poe1",
        session_date="2025-01-15",
        stats={"keep_count": 5},
    )
    temp_db.save_verdict_statistics(
        league="League2",
        game_version="poe2",
        session_date="2025-01-15",
        stats={"keep_count": 10},
    )

    deleted = temp_db.clear_verdict_statistics()

    assert deleted == 2
    assert temp_db.get_verdict_statistics("League1", "poe1", "2025-01-15") is None
    assert temp_db.get_verdict_statistics("League2", "poe2", "2025-01-15") is None


def test_clear_verdict_statistics_by_league(temp_db):
    """Test clearing verdict statistics by league."""
    temp_db.save_verdict_statistics(
        league="League1",
        game_version="poe1",
        session_date="2025-01-15",
        stats={"keep_count": 5},
    )
    temp_db.save_verdict_statistics(
        league="League2",
        game_version="poe1",
        session_date="2025-01-15",
        stats={"keep_count": 10},
    )

    deleted = temp_db.clear_verdict_statistics(league="League1")

    assert deleted == 1
    assert temp_db.get_verdict_statistics("League1", "poe1", "2025-01-15") is None
    assert temp_db.get_verdict_statistics("League2", "poe1", "2025-01-15") is not None
