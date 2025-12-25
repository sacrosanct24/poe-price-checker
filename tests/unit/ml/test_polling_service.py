"""Tests for ml/collection/polling_service.py."""

from data_sources.mod_database import ModDatabase
from ml.collection.polling_service import MLPollingService


class FakeTradeClient:
    def __init__(self, listings):
        self.listings = listings
        self.last_query = None

    def post(self, _endpoint, data=None, params=None, timeout_override=None):
        self.last_query = data
        return {"id": "search-1", "result": ["listing-1"]}

    def get(self, _endpoint, params=None, use_cache=True, ttl_override=None, timeout_override=None):
        return {"result": self.listings}


def test_polling_service_inserts_listings(temp_db, tmp_path):
    mod_db = ModDatabase(db_path=tmp_path / "mods.db")
    mod_db.conn.execute(
        """
        INSERT INTO mods (id, stat_text_raw, tier_text)
        VALUES (?, ?, ?)
        """,
        ("mod_life_t1", "+(70-79) to maximum Life", "Tier 1"),
    )
    mod_db.conn.commit()

    listings = [
        {
            "id": "listing-1",
            "listing": {
                "price": {"amount": 12, "currency": "chaos"},
                "account": {"name": "SellerOne"},
            },
            "item": {
                "name": "",
                "typeLine": "Titan Greaves",
                "baseType": "Titan Greaves",
                "ilvl": 86,
                "explicitMods": ["+75 to maximum Life"],
                "category": {"armour": ["boots"]},
            },
        }
    ]

    service = MLPollingService(
        {
            "enabled": True,
            "league": "Standard",
            "game_id": "poe1",
            "base_types": ["Titan Greaves"],
            "max_listings_per_base": 10,
        },
        db=temp_db,
        mod_database=mod_db,
        trade_client=FakeTradeClient(listings),
        price_converter=lambda amount, currency: amount,
    )

    stats, seen_ids = service.poll_once()

    assert stats.listings_fetched == 1
    assert stats.listings_new == 1
    assert stats.listings_updated == 0
    assert seen_ids == ["listing-1"]
    assert service.trade_client.last_query["query"]["type"] == "Titan Greaves"

    row = temp_db.conn.execute(
        "SELECT base_type, price_chaos, seller_account FROM ml_listings"
    ).fetchone()

    assert row["base_type"] == "Titan Greaves"
    assert row["price_chaos"] == 12.0
    assert row["seller_account"] == "SellerOne"
    mod_db.close()
