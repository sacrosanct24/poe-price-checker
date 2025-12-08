"""
Shared test utilities and fake implementations for testing.

This module provides reusable test doubles (fakes, stubs) that can be used
across the test suite. Prefer these over MagicMock for complex dependencies.

Usage in tests:
    from tests.conftest_utils import FakeConfig, FakePriceSource, make_parsed_item
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock


# =============================================================================
# Fake Configuration
# =============================================================================


@dataclass
class FakeConfig:
    """
    Fake configuration object for testing.

    Usage:
        config = FakeConfig(current_game="poe1", league="Standard")
        service = MyService(config=config)
    """

    current_game: str = "poe1"
    league: str = "Standard"
    auto_detect_league: bool = False
    _settings: dict = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self._settings[key] = value

    def get_api_timeouts(self) -> tuple[float, float]:
        """Return default API timeouts."""
        return (5.0, 30.0)

    def get_pricing_ttls(self) -> dict[str, int]:
        """Return default pricing TTLs."""
        return {"currency": 300, "items": 600}


# =============================================================================
# Fake Database
# =============================================================================


class FakeDatabase:
    """
    In-memory fake database for testing.

    Usage:
        db = FakeDatabase()
        db.add_sale("Exalted Orb", 150.0)
        assert db.get_recent_sales() == [...]
    """

    def __init__(self):
        self._sales: list[dict[str, Any]] = []
        self._price_checks: list[dict[str, Any]] = []
        self._currency_rates: dict[str, float] = {}

    def record_instant_sale(
        self,
        item_name: str,
        price: float,
        currency: str = "chaos",
        **kwargs,
    ) -> int:
        """Record a sale and return sale ID."""
        sale_id = len(self._sales) + 1
        self._sales.append({
            "id": sale_id,
            "item_name": item_name,
            "price": price,
            "currency": currency,
            **kwargs,
        })
        return sale_id

    def get_recent_sales(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent sales."""
        return self._sales[-limit:]

    def record_currency_rate(self, currency: str, rate: float) -> None:
        """Record a currency exchange rate."""
        self._currency_rates[currency] = rate

    def get_currency_rate(self, currency: str) -> float | None:
        """Get a currency exchange rate."""
        return self._currency_rates.get(currency)

    def clear(self) -> None:
        """Clear all stored data."""
        self._sales.clear()
        self._price_checks.clear()
        self._currency_rates.clear()


# =============================================================================
# Fake Price Source
# =============================================================================


class FakePriceSource:
    """
    Controllable fake price source for testing.

    Usage:
        source = FakePriceSource()
        source.set_price("Exalted Orb", 150.0)
        result = source.check_item("Exalted Orb")
        assert result[0]["price"] == 150.0
    """

    def __init__(self, name: str = "fake_source"):
        self.name = name
        self._prices: dict[str, float] = {}
        self._errors: dict[str, Exception] = {}
        self.check_item_calls: list[str] = []

    def set_price(self, item_name: str, price: float) -> None:
        """Set price for an item."""
        self._prices[item_name] = price

    def set_error(self, item_name: str, error: Exception) -> None:
        """Set an error to raise for an item."""
        self._errors[item_name] = error

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        """Check price for an item."""
        self.check_item_calls.append(item_text)

        # Check for configured error
        if item_text in self._errors:
            raise self._errors[item_text]

        # Return price if configured
        if item_text in self._prices:
            return [{
                "source": self.name,
                "price": self._prices[item_text],
                "currency": "chaos",
                "item_name": item_text,
            }]

        # Default: no price found
        return []

    def clear(self) -> None:
        """Clear all configured prices and errors."""
        self._prices.clear()
        self._errors.clear()
        self.check_item_calls.clear()


# =============================================================================
# Parsed Item Factory
# =============================================================================


@dataclass
class MockParsedItem:
    """
    Mock parsed item for testing.

    Usage:
        item = make_parsed_item(name="Headhunter", rarity="Unique")
    """

    rarity: str = "Rare"
    name: str = "Test Item"
    base_type: str = "Leather Belt"
    item_level: int = 75
    explicit_mods: list[str] = field(default_factory=list)
    implicit_mods: list[str] = field(default_factory=list)
    corrupted: bool = False
    influenced: list[str] = field(default_factory=list)
    sockets: str = ""
    links: int = 0
    quality: int = 0
    identified: bool = True
    raw_text: str = ""

    @property
    def mods(self) -> list[str]:
        """All mods combined."""
        return self.implicit_mods + self.explicit_mods


def make_parsed_item(**kwargs) -> MockParsedItem:
    """
    Factory function for creating test parsed items.

    Usage:
        item = make_parsed_item(name="Headhunter", rarity="Unique")
        item = make_parsed_item(
            base_type="Imperial Claw",
            explicit_mods=["Adds 10 to 20 Fire Damage"]
        )
    """
    return MockParsedItem(**kwargs)


# =============================================================================
# Qt Signal Testing Helpers
# =============================================================================


def create_signal_recorder():
    """
    Create a callable that records all arguments it receives.

    Usage:
        recorder = create_signal_recorder()
        widget.some_signal.connect(recorder)
        widget.do_something()
        assert recorder.calls == [(arg1, arg2), ...]
    """

    class SignalRecorder:
        def __init__(self):
            self.calls: list[tuple] = []

        def __call__(self, *args):
            self.calls.append(args)

        def clear(self):
            self.calls.clear()

        @property
        def call_count(self) -> int:
            return len(self.calls)

        @property
        def last_call(self) -> tuple | None:
            return self.calls[-1] if self.calls else None

    return SignalRecorder()


def assert_signal_emitted(
    qtbot,
    signal,
    trigger_action,
    timeout: int = 1000,
    expected_args: tuple | None = None,
):
    """
    Assert that a signal is emitted when an action is triggered.

    Usage:
        assert_signal_emitted(
            qtbot,
            widget.clicked,
            lambda: qtbot.mouseClick(widget, Qt.LeftButton),
            expected_args=(True,)
        )
    """
    with qtbot.waitSignal(signal, timeout=timeout) as blocker:
        trigger_action()

    if expected_args is not None:
        assert tuple(blocker.args) == expected_args


def assert_signal_not_emitted(qtbot, signal, trigger_action, wait_ms: int = 100):
    """
    Assert that a signal is NOT emitted when an action is triggered.

    Usage:
        assert_signal_not_emitted(
            qtbot,
            widget.value_changed,
            lambda: widget.set_value(widget.current_value)  # Same value
        )
    """
    from PyQt6.QtWidgets import QApplication

    recorder = create_signal_recorder()
    signal.connect(recorder)

    try:
        trigger_action()
        QApplication.processEvents()
        assert recorder.call_count == 0, f"Signal was emitted {recorder.call_count} times"
    finally:
        signal.disconnect(recorder)


# =============================================================================
# API Response Builders
# =============================================================================


def make_api_response(
    status: str = "success",
    data: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """
    Create a mock API response.

    Usage:
        response = make_api_response(data={"price": 100})
        mock_client.fetch.return_value = response
    """
    return {
        "status": status,
        "data": data or {},
        "error": error,
    }


def make_price_row(
    source: str = "poe.ninja",
    price: float = 100.0,
    currency: str = "chaos",
    confidence: float = 0.9,
    **kwargs,
) -> dict[str, Any]:
    """
    Create a mock price row.

    Usage:
        row = make_price_row(source="trade", price=150.0)
    """
    return {
        "source": source,
        "price": price,
        "currency": currency,
        "confidence": confidence,
        **kwargs,
    }


# =============================================================================
# Test Data Constants
# =============================================================================


SAMPLE_CURRENCY_ITEM = """Rarity: Currency
Divine Orb
--------
Stack Size: 1/20
--------
Randomises the numeric values of the random modifiers on a piece of equipment.
--------
"""

SAMPLE_RARE_ITEM = """Rarity: Rare
Apocalypse Knuckle
Imperial Claw
--------
Quality: +20% (augmented)
Attacks per Second: 1.82
--------
Requires Level 68, 131 Dex, 95 Int
--------
+46 Life gained for each Enemy hit by Attacks (implicit)
--------
Adds 25 to 50 Physical Damage
+37% to Critical Strike Multiplier
+45 to maximum Life
+32% to Fire Resistance
--------
"""

SAMPLE_UNIQUE_ITEM = """Rarity: Unique
Headhunter
Leather Belt
--------
Requires Level 40
--------
+25 to maximum Life (implicit)
--------
+63 to Strength
+63 to Dexterity
+40 to maximum Life
+23% to Cold Resistance
When you Kill a Rare Monster, you gain its Modifiers for 20 seconds
--------
"""
