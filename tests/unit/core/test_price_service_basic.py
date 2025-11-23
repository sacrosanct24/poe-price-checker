from __future__ import annotations

import pytest
from datetime import datetime

from core.price_service import PriceService
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


# --------------------------------------------
# Fakes aligned with real PriceService behavior
# --------------------------------------------

class FakeConfig:
    current_game = GameVersion.POE1.value
    league = "Crucible"
    divine_rate = None
    auto_detect_league = False
    games = {
        "poe1": {"league": "Crucible", "divine_chaos_rate": None}
    }


class FakeParsedItem:
    def __init__(self):
        self.name = "Goldrim"
        self.base_type = "Leather Cap"
        self.rarity = "Unique"
        self.links = 6
        self.variant = ""
        self.is_corrupted = False
        self.gem_level = None
        self.gem_quality = None


class FakeParser:
    def parse(self, text):
        if not text.strip():
            return None
        return FakeParsedItem()


class FakeDB:
    """
    Matches real PriceService expectations:
    - create_price_check(...)
    - add_price_quotes_batch(check_id, rows)
    - get_latest_price_stats_for_item(...)
    """
    def __init__(self):
        self.check_rows = []
        self.quote_rows = []

    def create_price_check(
        self,
        game_version,
        league,
        item_name,
        item_base_type,
        source,
        query_hash
    ):
        row_id = len(self.check_rows) + 1
        self.check_rows.append({
            "id": row_id,
            "game_version": game_version,
            "league": league,
            "item_name": item_name,
            "item_base_type": item_base_type,
            "source": source,
            "query_hash": query_hash,
        })
        return row_id

    def add_price_quotes_batch(self, check_id, rows):
        for r in rows:
            self.quote_rows.append((check_id, r))

    def get_latest_price_stats_for_item(
        self,
        game_version,
        league,
        item_name,
        base_type,
    ):
        return None


class FakePoeNinja:
    def __init__(self):
        self.divine_chaos_rate = 200.0

    def find_item_price(
        self,
        item_name,
        base_type,
        rarity,
        gem_level,
        gem_quality,
        corrupted
    ):
        # Minimal valid response
        return {
            "chaosValue": 5.0,
            "listingCount": 10,
        }


# --------------------------------------------
# Tests
# --------------------------------------------

def test_check_item_basic_flow():
    config = FakeConfig()
    parser = FakeParser()
    db = FakeDB()
    poe_ninja = FakePoeNinja()

    svc = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        trade_source=None,
    )

    rows = svc.check_item("Goldrim Leather Cap")
    assert len(rows) == 1

    gui_row = rows[0]
    assert gui_row["item_name"] == "Goldrim"
    assert gui_row["variant"] == ""
    assert gui_row["links"] == "6"
    assert gui_row["chaos_value"] == "5.0"
    assert gui_row["divine_value"] == "0.03"  # 5/200 rounded to 2 decimals
    assert gui_row["listing_count"] == "10"
    assert "poe.ninja" in gui_row["source"]

    # DB inserts
    assert len(db.check_rows) == 1
    assert len(db.quote_rows) == 1


def test_blank_text_returns_empty_and_does_not_hit_db():
    config = FakeConfig()
    parser = FakeParser()
    db = FakeDB()
    poe_ninja = FakePoeNinja()

    svc = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        trade_source=None,
    )

    rows = svc.check_item("   ")
    assert rows == []
    assert db.check_rows == []
    assert db.quote_rows == []
