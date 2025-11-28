# tests/test_clipboard_monitor.py
"""
Tests for ClipboardMonitor - clipboard monitoring and PoE item detection.
"""

from __future__ import annotations

import pytest
from dataclasses import asdict

from core.clipboard_monitor import (
    ClipboardMonitor,
    HotkeyConfig,
    PriceCheckHotkeyManager,
)


class TestHotkeyConfig:
    """Tests for HotkeyConfig dataclass."""

    def test_default_enabled(self):
        """Hotkey is enabled by default."""
        config = HotkeyConfig(hotkey="ctrl+shift+c", description="Test")
        assert config.enabled is True

    def test_explicit_disabled(self):
        """Hotkey can be explicitly disabled."""
        config = HotkeyConfig(hotkey="ctrl+shift+c", description="Test", enabled=False)
        assert config.enabled is False

    def test_asdict(self):
        """Config can be converted to dict."""
        config = HotkeyConfig(hotkey="ctrl+c", description="Copy")
        data = asdict(config)
        assert data == {"hotkey": "ctrl+c", "description": "Copy", "enabled": True}


class TestClipboardMonitorPoeDetection:
    """Tests for PoE item detection logic."""

    @pytest.fixture
    def monitor(self):
        """Create monitor instance."""
        return ClipboardMonitor()

    def test_detect_rare_item(self, monitor):
        """Detect a rare item with standard format."""
        item_text = """Item Class: Body Armours
Rarity: Rare
Doom Shell
Vaal Regalia
--------
Item Level: 86
--------
+80 to maximum Life
+40% to Fire Resistance"""
        assert monitor._is_poe_item(item_text) is True

    def test_detect_unique_item(self, monitor):
        """Detect a unique item."""
        item_text = """Item Class: Belts
Rarity: Unique
Headhunter
Leather Belt
--------
Item Level: 44
--------
+40 to maximum Life
--------
When you Kill a Rare monster, you gain its Modifiers for 60 seconds"""
        assert monitor._is_poe_item(item_text) is True

    def test_detect_magic_item(self, monitor):
        """Detect a magic item."""
        item_text = """Item Class: Rings
Rarity: Magic
Ruby Ring of Heat
--------
Item Level: 75
--------
+30% to Fire Resistance
--------
+15% to Cold Resistance"""
        assert monitor._is_poe_item(item_text) is True

    def test_reject_empty_text(self, monitor):
        """Reject empty text."""
        assert monitor._is_poe_item("") is False
        assert monitor._is_poe_item(None) is False

    def test_reject_short_text(self, monitor):
        """Reject text that's too short."""
        assert monitor._is_poe_item("Rarity: Rare") is False
        assert monitor._is_poe_item("Item Level") is False

    def test_reject_regular_text(self, monitor):
        """Reject regular text that's not a PoE item."""
        assert monitor._is_poe_item("This is just regular text") is False
        assert monitor._is_poe_item("Hello world! How are you today?") is False

    def test_reject_code(self, monitor):
        """Reject code that might look similar."""
        code = """def get_item():
    rarity = "Rare"
    return {"name": "Test Item", "level": 86}"""
        assert monitor._is_poe_item(code) is False

    def test_reject_oversized_content(self, monitor):
        """Reject suspiciously large clipboard content."""
        huge_text = "Rarity: Rare\n--------\nItem Level: 86\n--------\n" + "a" * 200000
        assert monitor._is_poe_item(huge_text) is False

    def test_poe_indicators_constant(self, monitor):
        """Verify expected indicators exist."""
        assert "Rarity:" in monitor.POE_ITEM_INDICATORS
        assert "Item Class:" in monitor.POE_ITEM_INDICATORS
        assert "--------" in monitor.POE_ITEM_INDICATORS
        assert "Item Level:" in monitor.POE_ITEM_INDICATORS


class TestClipboardMonitorStats:
    """Tests for monitor statistics."""

    def test_initial_stats(self):
        """Stats start at zero."""
        monitor = ClipboardMonitor()
        stats = monitor.get_stats()

        assert stats["running"] is False
        assert stats["items_detected"] == 0
        assert stats["clipboard_reads"] == 0
        assert stats["hotkeys_registered"] == 0
        assert stats["hotkeys"] == []

    def test_stats_increment(self):
        """Stats increment when operations happen."""
        monitor = ClipboardMonitor()

        # Simulate clipboard read (bypass actual clipboard)
        monitor.clipboard_reads = 5
        monitor.items_detected = 2

        stats = monitor.get_stats()
        assert stats["clipboard_reads"] == 5
        assert stats["items_detected"] == 2

    def test_is_running_property(self):
        """is_running property reflects state."""
        monitor = ClipboardMonitor()
        assert monitor.is_running is False

        monitor._running = True
        assert monitor.is_running is True


class TestClipboardMonitorLifecycle:
    """Tests for monitor start/stop lifecycle."""

    def test_start_monitoring(self):
        """Monitor can start."""
        monitor = ClipboardMonitor()

        result = monitor.start_monitoring()
        assert result is True
        assert monitor.is_running is True

        # Cleanup
        monitor.stop_monitoring()
        assert monitor.is_running is False

    def test_start_twice_fails(self):
        """Starting twice returns False."""
        monitor = ClipboardMonitor()

        result1 = monitor.start_monitoring()
        result2 = monitor.start_monitoring()

        assert result1 is True
        assert result2 is False  # Already running

        monitor.stop_monitoring()

    def test_cleanup(self):
        """cleanup() stops monitoring."""
        monitor = ClipboardMonitor()
        monitor.start_monitoring()

        monitor.cleanup()
        assert monitor.is_running is False


class TestClipboardMonitorCheckNow:
    """Tests for check_clipboard_now method."""

    def test_check_returns_none_for_non_item(self):
        """Returns None when no PoE item."""
        monitor = ClipboardMonitor()

        # Mock clipboard to return regular text
        monitor._get_clipboard = lambda: "regular text"

        result = monitor.check_clipboard_now()
        assert result is None

    def test_check_returns_item_text(self):
        """Returns item text when PoE item found."""
        monitor = ClipboardMonitor()

        item_text = """Item Class: Boots
Rarity: Rare
Storm Track
Slink Boots
--------
Item Level: 85
--------
+30% to Cold Resistance"""

        # Mock clipboard
        monitor._get_clipboard = lambda: item_text

        result = monitor.check_clipboard_now()
        assert result == item_text


class TestPriceCheckHotkeyManager:
    """Tests for PriceCheckHotkeyManager."""

    def test_default_hotkeys(self):
        """Check default hotkey constants."""
        assert PriceCheckHotkeyManager.DEFAULT_PRICE_CHECK_HOTKEY == "ctrl+shift+c"
        assert PriceCheckHotkeyManager.DEFAULT_PASTE_CHECK_HOTKEY == "ctrl+shift+v"

    def test_manager_creates_monitor(self):
        """Manager creates a ClipboardMonitor."""
        def dummy_callback(text):
            pass

        manager = PriceCheckHotkeyManager(dummy_callback)
        assert isinstance(manager.monitor, ClipboardMonitor)

        manager.cleanup()

    def test_manager_cleanup(self):
        """Manager cleanup stops monitor."""
        def dummy_callback(text):
            pass

        manager = PriceCheckHotkeyManager(dummy_callback)
        manager.cleanup()

        assert manager.monitor.is_running is False
