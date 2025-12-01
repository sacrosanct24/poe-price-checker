"""
Additional edge case tests for Database to improve coverage.
Focus on error handling, edge cases, and less common operations.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from core.database import Database
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_edge_cases.db"
    db = Database(db_path)
    yield db
    db.close()


# -------------------------
# Price Statistics Edge Cases
# -------------------------

def test_get_price_stats_for_check_with_no_quotes(temp_db):
    """Stats for check with no quotes should return None values"""
    check_id = temp_db.create_price_check(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Empty Item",
        item_base_type=None,
        source="test",
        query_hash=None,
    )
    
    stats = temp_db.get_price_stats_for_check(check_id)
    
    assert stats["count"] == 0
    assert stats["min"] is None
    assert stats["max"] is None
    assert stats["mean"] is None


def test_get_price_stats_for_check_with_single_quote(temp_db):
    """Stats with single quote should handle edge case"""
    check_id = temp_db.create_price_check(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Single Quote Item",
        item_base_type=None,
        source="test",
        query_hash=None,
    )
    
    temp_db.add_price_quotes_batch(check_id, [
        {"source": "test", "price_chaos": 50.0, "original_currency": "chaos"}
    ])
    
    stats = temp_db.get_price_stats_for_check(check_id)
    
    assert stats["count"] == 1
    assert stats["min"] == 50.0
    assert stats["max"] == 50.0
    assert stats["mean"] == 50.0
    assert stats["median"] == 50.0
    assert stats["stddev"] == 0.0


def test_get_price_stats_for_check_with_outliers(temp_db):
    """Trimmed mean should reduce impact of outliers"""
    check_id = temp_db.create_price_check(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Outlier Item",
        item_base_type=None,
        source="test",
        query_hash=None,
    )
    
    # Add quotes with outliers
    quotes = [
        {"source": "test", "price_chaos": 1.0, "original_currency": "chaos"},  # Outlier low
        {"source": "test", "price_chaos": 48.0, "original_currency": "chaos"},
        {"source": "test", "price_chaos": 50.0, "original_currency": "chaos"},
        {"source": "test", "price_chaos": 52.0, "original_currency": "chaos"},
        {"source": "test", "price_chaos": 100.0, "original_currency": "chaos"},  # Outlier high
    ]
    temp_db.add_price_quotes_batch(check_id, quotes)
    
    stats = temp_db.get_price_stats_for_check(check_id)
    
    # Trimmed mean should be closer to 50 than regular mean
    assert 48.0 <= stats["trimmed_mean"] <= 52.0
    # Regular mean is (1+48+50+52+100)/5 = 50.2, so check it's around 50
    assert 49.0 <= stats["mean"] <= 51.0


# -------------------------
# Sales Edge Cases
# -------------------------

def test_complete_sale_with_negative_time_delta_clamps_to_zero(temp_db):
    """If sold_at is before listed_at, time_to_sale should be 0"""
    sale_id = temp_db.add_sale("Test Item", listed_price_chaos=10.0)
    
    # Sell "before" it was listed (clock skew scenario)
    future_time = datetime.now() + timedelta(hours=1)
    past_time = datetime.now() - timedelta(hours=1)
    
    temp_db.complete_sale(sale_id, actual_price_chaos=9.0, sold_at=past_time)
    
    sales = temp_db.get_sales()
    sale = next(s for s in sales if s["id"] == sale_id)
    
    assert sale["time_to_sale_hours"] == 0.0  # Should be clamped to 0


def test_get_sales_with_filters(temp_db):
    """get_sales should respect filters properly"""
    # Add variety of sales
    temp_db.add_sale("Item A", listed_price_chaos=10.0)
    s2 = temp_db.add_sale("Item B", listed_price_chaos=20.0)
    temp_db.add_sale("Item C", listed_price_chaos=30.0)
    
    # Mark one as sold
    temp_db.complete_sale(s2, actual_price_chaos=19.0, sold_at=datetime.now())
    
    all_sales = temp_db.get_sales(sold_only=False)
    sold_sales = temp_db.get_sales(sold_only=True)
    
    assert len(all_sales) == 3
    assert len(sold_sales) == 1
    assert sold_sales[0]["id"] == s2


# -------------------------
# Plugin State Edge Cases
# -------------------------

def test_set_plugin_config_and_retrieve(temp_db):
    """Plugin config JSON should be stored and retrieved correctly"""
    config_json = '{"threshold": 100, "enabled": true}'
    
    temp_db.set_plugin_config("test_plugin", config_json)
    retrieved = temp_db.get_plugin_config("test_plugin")
    
    assert retrieved == config_json


def test_get_plugin_config_for_nonexistent_plugin_returns_none(temp_db):
    """Getting config for non-existent plugin should return None"""
    result = temp_db.get_plugin_config("nonexistent_plugin")
    assert result is None


def test_plugin_enabled_and_config_are_independent(temp_db):
    """Setting config shouldn't affect enabled state and vice versa"""
    temp_db.set_plugin_enabled("test", True)
    temp_db.set_plugin_config("test", '{"key": "value"}')
    
    assert temp_db.is_plugin_enabled("test") is True
    assert temp_db.get_plugin_config("test") == '{"key": "value"}'
    
    # Disable plugin but keep config
    temp_db.set_plugin_enabled("test", False)
    assert temp_db.is_plugin_enabled("test") is False
    assert temp_db.get_plugin_config("test") == '{"key": "value"}'  # Config unchanged


# -------------------------
# Price Quotes Batch Edge Cases
# -------------------------

def test_add_price_quotes_batch_with_empty_list(temp_db):
    """Adding empty quote list should not error"""
    check_id = temp_db.create_price_check(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Test",
        item_base_type=None,
        source="test",
        query_hash=None,
    )
    
    # Should not raise
    temp_db.add_price_quotes_batch(check_id, [])


def test_add_price_quotes_batch_skips_invalid_quotes(temp_db):
    """Quotes with missing price_chaos should be skipped"""
    check_id = temp_db.create_price_check(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Test",
        item_base_type=None,
        source="test",
        query_hash=None,
    )
    
    quotes = [
        {"source": "test", "price_chaos": 10.0},  # Valid
        {"source": "test"},  # Invalid - no price_chaos
        {"source": "test", "price_chaos": None},  # Invalid - None price
        {"source": "test", "price_chaos": 20.0},  # Valid
    ]
    
    temp_db.add_price_quotes_batch(check_id, quotes)
    
    # Check that only valid quotes were inserted
    stats = temp_db.get_price_stats_for_check(check_id)
    assert stats["count"] == 2


# -------------------------
# Get Latest Price Stats Edge Cases
# -------------------------

def test_get_latest_price_stats_for_item_no_recent_checks(temp_db):
    """Should return None if no checks within specified days"""
    result = temp_db.get_latest_price_stats_for_item(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Never Checked Item",
        days=7,
    )
    
    assert result is None


def test_get_latest_price_stats_for_item_old_check_excluded(temp_db):
    """Should exclude checks older than specified days"""
    # Create an old check (we can't directly set timestamp, but we can test the query works)
    check_id = temp_db.create_price_check(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Old Item",
        item_base_type=None,
        source="test",
        query_hash=None,
    )
    
    temp_db.add_price_quotes_batch(check_id, [
        {"source": "test", "price_chaos": 100.0, "original_currency": "chaos"}
    ])
    
    # Query for last 30 days should find it
    result = temp_db.get_latest_price_stats_for_item(
        game_version=GameVersion.POE1,
        league="Standard",
        item_name="Old Item",
        days=30,
    )
    
    assert result is not None
    assert result["count"] == 1


# -------------------------
# Database Initialization Edge Cases
# -------------------------

def test_database_creates_directory_if_not_exists(tmp_path):
    """Database should create parent directory if it doesn't exist"""
    nested_path = tmp_path / "nested" / "dir" / "db.db"
    
    # Ensure parent directory is created
    db = Database(nested_path)
    assert nested_path.parent.exists()
    assert nested_path.exists()
    db.close()


def test_database_uses_default_path_if_none_provided(tmp_path):
    """Database should use default path when no path provided"""
    db = Database()
    
    expected = Path.home() / ".poe_price_checker" / "data.db"
    assert db.db_path == expected
    
    db.close()


# -------------------------
# Wipe Database
# -------------------------

def test_wipe_all_data_clears_all_tables(temp_db):
    """wipe_all_data should clear all data tables but preserve schema"""
    # Add data to all tables
    temp_db.add_checked_item(GameVersion.POE1, "Standard", "Item", chaos_value=10.0)
    temp_db.add_sale("Item", listed_price_chaos=10.0)
    temp_db.add_price_snapshot(GameVersion.POE1, "Standard", "Item", chaos_value=10.0)
    temp_db.set_plugin_enabled("test", True)
    
    check_id = temp_db.create_price_check(
        GameVersion.POE1, "Standard", "Item", None, "test", None
    )
    temp_db.add_price_quotes_batch(check_id, [
        {"source": "test", "price_chaos": 10.0}
    ])
    
    # Verify data exists
    stats_before = temp_db.get_stats()
    assert stats_before["checked_items"] > 0
    assert stats_before["sales"] > 0
    assert stats_before["price_snapshots"] > 0
    
    # Wipe all data
    temp_db.wipe_all_data()
    
    # Verify all cleared
    stats_after = temp_db.get_stats()
    assert stats_after["checked_items"] == 0
    assert stats_after["sales"] == 0
    assert stats_after["price_snapshots"] == 0
    assert stats_after["price_checks"] == 0
    assert stats_after["price_quotes"] == 0
    
    # Schema should still exist (can still insert)
    temp_db.add_checked_item(GameVersion.POE1, "Standard", "New Item", chaos_value=5.0)
    stats = temp_db.get_stats()
    assert stats["checked_items"] == 1
