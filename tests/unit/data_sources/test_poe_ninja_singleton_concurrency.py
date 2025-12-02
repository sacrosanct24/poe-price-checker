from __future__ import annotations

import threading
import pytest


pytestmark = pytest.mark.unit


def test_get_ninja_price_two_threads_build_once(monkeypatch):
    """
    Ensure that two concurrent callers of get_ninja_price cause only a single
    build of the price database, and both callers receive a price result.
    The implementation builds outside the lock and publishes with a short lock
    (double-checked), so this should be safe and efficient.
    """
    # Import inside test to get fresh globals for monkeypatch to work reliably
    import data_sources.poe_ninja_client as mod

    # Reset singleton globals
    mod._price_db = None
    mod._client = None

    # Dummy price object
    class DummyPrice:
        def __init__(self, name: str):
            self.name = name
            self.chaos_value = 123.0
            self.display_price = "123c"

    # Dummy DB to return a fixed price
    class DummyDB:
        def __init__(self, league: str):
            self.league = league

        def get_price(self, name: str):
            return DummyPrice(name)

    # Counter to ensure single build
    build_calls = {"n": 0}

    class DummyClient:
        def build_price_database(self, league: str, progress_callback=None):
            build_calls["n"] += 1
            return DummyDB(league)

    # Monkeypatch client factory to return our dummy client
    def fake_get_client():
        return DummyClient()

    monkeypatch.setattr(mod, "get_ninja_client", fake_get_client)

    # Run two threads that call get_ninja_price concurrently
    start = threading.Barrier(3)
    results: list = []

    def worker():
        start.wait()
        price = mod.get_ninja_price("Some Item", league="StdLeague")
        results.append(price)

    t1 = threading.Thread(target=worker, daemon=True)
    t2 = threading.Thread(target=worker, daemon=True)
    t1.start()
    t2.start()

    # Release both workers
    start.wait()

    t1.join(timeout=2)
    t2.join(timeout=2)

    assert len(results) == 2, "Both threads should return"
    # Both prices should be DummyPrice objects with expected value
    for p in results:
        assert getattr(p, "display_price", None) == "123c"

    # Only one build should have happened despite two callers
    assert build_calls["n"] == 1
