import types

from core.price_multi import MultiSourcePriceService


class DummySource:
    def __init__(self, name: str):
        self.name = name

    def check_item(self, item_text: str):
        return []


def test_enabled_sources_callback_persists_state():
    s1 = DummySource("A")
    s2 = DummySource("B")
    captured = {}

    def on_change(state):
        captured.clear()
        captured.update(state)

    svc = MultiSourcePriceService([s1, s2], on_change_enabled_state=on_change)

    # Baseline: all enabled by default
    baseline = svc.get_enabled_state()
    assert baseline == {"A": True, "B": True}

    # Disable one source
    svc.set_enabled_state({"A": True, "B": False})
    assert svc.get_enabled_state() == {"A": True, "B": False}
    # Callback should have been invoked with current state
    assert captured == {"A": True, "B": False}


def test_enabled_sources_all_disabled_falls_back_to_all_enabled():
    s1 = DummySource("A")
    s2 = DummySource("B")
    captured = {}

    def on_change(state):
        captured.clear()
        captured.update(state)

    svc = MultiSourcePriceService([s1, s2], on_change_enabled_state=on_change)

    # If caller disables all, service falls back to all enabled
    svc.set_enabled_state({"A": False, "B": False})
    assert svc.get_enabled_state() == {"A": True, "B": True}
    assert captured == {"A": True, "B": True}
