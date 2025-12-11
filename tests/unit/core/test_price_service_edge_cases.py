"""
Additional edge case tests for PriceService to improve coverage.
These tests focus on error handling and less common code paths.
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock
from core.pricing import PriceService
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


class FakeConfig:
    """Minimal config for edge case testing"""
    current_game = GameVersion.POE1
    league = "Standard"
    divine_rate = None
    
    def __init__(self):
        self.games = {
            "poe1": {"league": "Standard", "divine_chaos_rate": None},
            "poe2": {"league": "Standard", "divine_chaos_rate": None},
        }


class FakeParser:
    def parse(self, text):
        return Mock(
            name="Test Item",
            base_type="Test Base",
            rarity="UNIQUE",
            item_level=80,
            links=0,
            variant="",
            gem_level=None,
            gem_quality=None,
            is_corrupted=False
        )


class FakeDB:
    def __init__(self):
        self.price_checks = []
        self.quotes_batches = []
        self._next_id = 1
    
    def create_price_check(self, game_version, league, item_name, item_base_type, source, query_hash):
        check_id = self._next_id
        self._next_id += 1
        self.price_checks.append({
            "id": check_id,
            "game_version": game_version,
            "league": league,
            "item_name": item_name,
        })
        return check_id
    
    def add_price_quotes_batch(self, check_id, rows):
        self.quotes_batches.append((check_id, list(rows)))
    
    def get_latest_price_stats_for_item(self, game_version, league, item_name, days):
        return None


def test_check_item_with_empty_string_returns_empty():
    """Empty or whitespace-only input should return empty list"""
    svc = PriceService(
        config=FakeConfig(),
        parser=FakeParser(),
        db=FakeDB(),
        poe_ninja=None,
        trade_source=None,
    )
    
    assert svc.check_item("") == []
    assert svc.check_item("   ") == []
    assert svc.check_item("\n\t  ") == []


def test_check_item_with_no_poe_ninja_returns_zero_price():
    """When poe_ninja is None, should return zero-price result"""
    svc = PriceService(
        config=FakeConfig(),
        parser=FakeParser(),
        db=FakeDB(),
        poe_ninja=None,
        poe_watch=None,
        trade_source=None,
    )
    
    rows = svc.check_item("Some Item Text")
    
    assert len(rows) == 1
    assert rows[0]["chaos_value"] == "0.0"
    assert rows[0]["listing_count"] == "0"
    assert "no pricing sources" in rows[0]["source"].lower()


def test_save_trade_quotes_skips_invalid_quotes():
    """Quotes with missing price_chaos should be skipped"""
    db = FakeDB()
    poe_ninja = Mock()
    poe_ninja.divine_chaos_rate = 200.0
    
    svc = PriceService(
        config=FakeConfig(),
        parser=FakeParser(),
        db=db,
        poe_ninja=poe_ninja,
        trade_source=None,
    )
    
    # Create a parsed item
    parsed = Mock(
        display_name="Test Item",
        name="Test Item",
        base_type="Test Base",
    )
    
    # Mix of valid and invalid quotes
    trade_quotes = [
        {"amount": 10.0, "original_currency": "chaos"},  # Valid
        {"amount": None, "original_currency": "chaos"},  # Invalid - no amount
        {"original_currency": "chaos"},  # Invalid - no amount key
        {"amount": 5.0, "original_currency": "exalted"},  # Invalid - unsupported currency
    ]
    
    svc._save_trade_quotes_for_check(parsed, trade_quotes, poe_ninja_chaos=50.0)
    
    # Should have 1 price check
    assert len(db.price_checks) == 1
    
    # Should have 1 batch with 2 quotes (poe_ninja synthetic + 1 valid trade)
    assert len(db.quotes_batches) == 1
    check_id, quotes = db.quotes_batches[0]
    assert len(quotes) == 2
    
    sources = [q["source"] for q in quotes]
    assert "poe_ninja" in sources
    assert "trade" in sources


def test_convert_chaos_to_divines_with_zero_rate_returns_zero():
    """When divine rate is 0 or invalid, should return 0.0"""
    poe_ninja = Mock()
    poe_ninja.divine_chaos_rate = 0.0
    
    svc = PriceService(
        config=FakeConfig(),
        parser=FakeParser(),
        db=FakeDB(),
        poe_ninja=poe_ninja,
        trade_source=None,
    )
    
    # Should return 0.0 when rate is too low
    result = svc._convert_chaos_to_divines(100.0)
    assert result == 0.0


def test_convert_chaos_to_divines_with_config_override():
    """Config divine_rate should take precedence over poe_ninja"""
    cfg = FakeConfig()
    cfg.divine_rate = 250.0  # Explicit override
    
    poe_ninja = Mock()
    poe_ninja.divine_chaos_rate = 200.0  # Should be ignored
    
    svc = PriceService(
        config=cfg,
        parser=FakeParser(),
        db=FakeDB(),
        poe_ninja=poe_ninja,
        trade_source=None,
    )
    
    result = svc._convert_chaos_to_divines(250.0)
    assert result == 1.0  # 250 chaos / 250 rate = 1 divine


def test_get_item_display_name_fallbacks():
    """Should try multiple attributes to find item name"""
    svc = PriceService(
        config=FakeConfig(),
        parser=FakeParser(),
        db=FakeDB(),
        poe_ninja=None,
        trade_source=None,
    )
    
    # Test with display_name
    class ParsedWithDisplay:
        display_name = "Display Name"
        name = "Name"

    assert svc._get_item_display_name(ParsedWithDisplay()) == "Display Name"

    # Test fallback to name
    class ParsedWithName:
        display_name = None
        name = "Item Name"

    assert svc._get_item_display_name(ParsedWithName()) == "Item Name"

    # Test fallback to Unknown
    class ParsedEmpty:
        pass

    assert svc._get_item_display_name(ParsedEmpty()) == "Unknown Item"


def test_get_corrupted_flag_handles_various_formats():
    """Should handle bool, string, and None values for corrupted flag"""
    svc = PriceService(
        config=FakeConfig(),
        parser=FakeParser(),
        db=FakeDB(),
        poe_ninja=None,
        trade_source=None,
    )
    
    # Boolean values
    parsed = Mock(corrupted=True)
    assert svc._get_corrupted_flag(parsed) is True
    
    parsed = Mock(corrupted=False)
    assert svc._get_corrupted_flag(parsed) is False
    
    # String values
    parsed = Mock(corrupted="Corrupted")
    assert svc._get_corrupted_flag(parsed) is True
    
    parsed = Mock(corrupted="")
    assert svc._get_corrupted_flag(parsed) is False
    
    # None value
    parsed = Mock(corrupted=None)
    assert svc._get_corrupted_flag(parsed) is None
    
    # Missing attribute
    parsed = Mock(spec=[])
    assert svc._get_corrupted_flag(parsed) is None


def test_compute_display_price_with_no_listings():
    """Should return None values and 'none' confidence with 0 listings"""
    stats = {"count": 0}
    
    result = PriceService.compute_display_price(stats)
    
    assert result["display_price"] is None
    assert result["rounded_price"] is None
    assert result["confidence"] == "none"
    assert "No listings" in result["reason"]


def test_compute_display_price_rounding_policies():
    """Should round prices according to value ranges"""
    # High value (>= 100c): round to nearest 5
    stats = {
        "count": 20,
        "mean": 123.4,
        "median": 123.4,
        "trimmed_mean": 123.4,
        "p25": 120.0,
        "p75": 125.0,
        "stddev": 2.0,
    }
    result = PriceService.compute_display_price(stats)
    assert result["rounded_price"] == 125.0  # Rounded to nearest 5
    
    # Medium value (>= 10c): round to nearest 1
    stats["mean"] = stats["median"] = stats["trimmed_mean"] = 45.7
    stats["p25"] = 44.0
    stats["p75"] = 47.0
    result = PriceService.compute_display_price(stats)
    assert result["rounded_price"] == 46.0  # Rounded to nearest 1
    
    # Low value (>= 1c): 1 decimal
    stats["mean"] = stats["median"] = stats["trimmed_mean"] = 3.45
    stats["p25"] = 3.0
    stats["p75"] = 4.0
    result = PriceService.compute_display_price(stats)
    assert result["rounded_price"] == 3.5  # Rounded to 1 decimal
