"""Tests for ml/collection/lifecycle_tracker.py."""

from datetime import datetime, timedelta, timezone

from ml.collection.lifecycle_tracker import ListingLifecycleTracker


def _insert_listing(conn, listing_id, first_seen_at, state="LIVE"):
    conn.execute(
        """
        INSERT INTO ml_listings (
            listing_id,
            game_id,
            league,
            item_class,
            base_type,
            price_chaos,
            first_seen_at,
            last_seen_at,
            listing_state
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            listing_id,
            "poe1",
            "Standard",
            "Armour",
            "Titan Greaves",
            10.0,
            first_seen_at,
            first_seen_at,
            state,
        ),
    )


def test_lifecycle_transitions(temp_db):
    now = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    with temp_db.transaction() as conn:
        _insert_listing(conn, "live", (now - timedelta(days=3)).isoformat())
        _insert_listing(conn, "stale", (now - timedelta(days=8)).isoformat())
        _insert_listing(conn, "excluded", (now - timedelta(days=15)).isoformat())
        _insert_listing(conn, "missing_fast", (now - timedelta(hours=12)).isoformat())
        _insert_listing(conn, "missing_slow", (now - timedelta(days=2)).isoformat())

    tracker = ListingLifecycleTracker(temp_db, league="Standard", game_id="poe1")
    stats = tracker.update_listing_states(
        seen_listing_ids={"live", "stale", "excluded"},
        now=now,
    )

    assert stats.updated_visible == 3
    assert stats.updated_missing == 2

    rows = temp_db.conn.execute(
        "SELECT listing_id, listing_state, disappeared_at FROM ml_listings"
    ).fetchall()
    by_id = {row["listing_id"]: row for row in rows}

    assert by_id["live"]["listing_state"] == "LIVE"
    assert by_id["stale"]["listing_state"] == "STALE"
    assert by_id["excluded"]["listing_state"] == "EXCLUDED"

    assert by_id["missing_fast"]["listing_state"] == "DISAPPEARED_FAST"
    assert by_id["missing_fast"]["disappeared_at"] is not None
    assert by_id["missing_slow"]["listing_state"] == "DISAPPEARED_SLOW"
    assert by_id["missing_slow"]["disappeared_at"] is not None
