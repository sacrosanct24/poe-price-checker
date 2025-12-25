"""Integration test for a full ML collection cycle."""

from data_sources.mod_database import ModDatabase
from ml.collection.orchestrator import MLCollectionOrchestrator


class FakeTradeClient:
    def __init__(self, listings):
        self.listings = listings

    def post(self, _endpoint, data=None, params=None, timeout_override=None):
        return {"id": "search-1", "result": ["listing-1"]}

    def get(self, _endpoint, params=None, use_cache=True, ttl_override=None, timeout_override=None):
        return {"result": self.listings}


def test_collection_cycle(temp_db, tmp_path):
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
                "price": {"amount": 15, "currency": "chaos"},
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

    orchestrator = MLCollectionOrchestrator(
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

    stats = orchestrator.run_once()

    run_row = temp_db.conn.execute(
        "SELECT completed_at, listings_new FROM ml_collection_runs WHERE run_id = ?",
        (stats.run_id,),
    ).fetchone()

    assert run_row is not None
    assert run_row["completed_at"] is not None
    assert run_row["listings_new"] == 1

    listing_row = temp_db.conn.execute(
        "SELECT listing_state FROM ml_listings WHERE listing_id = ?",
        ("listing-1",),
    ).fetchone()

    assert listing_row["listing_state"] == "LIVE"
    mod_db.close()
