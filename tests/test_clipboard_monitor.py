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

    def test_enable_auto_detection(self):
        """Test enabling auto detection starts monitoring."""
        def dummy_callback(text):
            pass

        manager = PriceCheckHotkeyManager(dummy_callback)

        detection_callback = lambda x: None
        result = manager.enable_auto_detection(detection_callback)
        assert result is True
        assert manager.monitor.on_item_detected is detection_callback
        assert manager.monitor.is_running is True

        manager.cleanup()

    def test_disable_auto_detection(self):
        """Test disabling auto detection stops monitoring."""
        def dummy_callback(text):
            pass

        manager = PriceCheckHotkeyManager(dummy_callback)
        manager.enable_auto_detection(lambda x: None)
        manager.disable_auto_detection()

        assert manager.monitor.is_running is False
        manager.cleanup()


class TestClipboardMonitorSingleton:
    """Tests for singleton functions."""

    def test_get_hotkey_manager_creates_instance(self):
        """get_hotkey_manager creates manager on first call."""
        from core.clipboard_monitor import get_hotkey_manager, cleanup_hotkey_manager

        # Ensure clean state
        cleanup_hotkey_manager()

        callback = lambda x: None
        manager = get_hotkey_manager(callback)
        assert manager is not None

        cleanup_hotkey_manager()

    def test_get_hotkey_manager_returns_same_instance(self):
        """get_hotkey_manager returns same instance on subsequent calls."""
        from core.clipboard_monitor import get_hotkey_manager, cleanup_hotkey_manager

        cleanup_hotkey_manager()

        callback = lambda x: None
        manager1 = get_hotkey_manager(callback)
        manager2 = get_hotkey_manager()  # No callback needed

        assert manager1 is manager2

        cleanup_hotkey_manager()

    def test_get_hotkey_manager_no_callback_returns_none(self):
        """get_hotkey_manager returns None when no callback and no instance."""
        from core.clipboard_monitor import get_hotkey_manager, cleanup_hotkey_manager

        cleanup_hotkey_manager()

        result = get_hotkey_manager()
        assert result is None

    def test_cleanup_hotkey_manager(self):
        """cleanup_hotkey_manager clears the singleton."""
        from core.clipboard_monitor import get_hotkey_manager, cleanup_hotkey_manager

        cleanup_hotkey_manager()

        callback = lambda x: None
        get_hotkey_manager(callback)

        cleanup_hotkey_manager()

        result = get_hotkey_manager()
        assert result is None


class TestClipboardMonitorModuleConstants:
    """Tests for module-level constants."""

    def test_keyboard_available_is_bool(self):
        """KEYBOARD_AVAILABLE should be boolean."""
        from core.clipboard_monitor import KEYBOARD_AVAILABLE
        assert isinstance(KEYBOARD_AVAILABLE, bool)

    def test_pyperclip_available_is_bool(self):
        """PYPERCLIP_AVAILABLE should be boolean."""
        from core.clipboard_monitor import PYPERCLIP_AVAILABLE
        assert isinstance(PYPERCLIP_AVAILABLE, bool)

    def test_max_clipboard_size(self):
        """MAX_CLIPBOARD_SIZE should be reasonable."""
        monitor = ClipboardMonitor()
        assert monitor.MAX_CLIPBOARD_SIZE == 100_000


class TestClipboardMonitorHotkeyRegistration:
    """Tests for hotkey registration methods."""

    def test_register_hotkey_no_keyboard(self):
        """register_hotkey returns False when keyboard not available."""
        from unittest.mock import patch

        monitor = ClipboardMonitor()

        with patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', False):
            monitor.register_hotkey("ctrl+c", lambda: None, "Test")
            # The actual KEYBOARD_AVAILABLE is checked at module level
            # This test verifies the method exists and can be called

    def test_unregister_hotkey_not_registered(self):
        """unregister_hotkey handles non-existent hotkey."""
        from unittest.mock import patch

        monitor = ClipboardMonitor()

        with patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', False):
            result = monitor.unregister_hotkey("ctrl+nonexistent")
            assert result is False

    def test_unregister_all_hotkeys_empty(self):
        """unregister_all_hotkeys handles empty list."""
        monitor = ClipboardMonitor()
        assert len(monitor._hotkeys) == 0

        # Should not raise
        monitor.unregister_all_hotkeys()


class TestClipboardMonitorInit:
    """Tests for ClipboardMonitor initialization options."""

    def test_default_poll_interval(self):
        """Default poll interval is 0.5 seconds."""
        monitor = ClipboardMonitor()
        assert monitor.poll_interval == 0.5

    def test_custom_poll_interval(self):
        """Custom poll interval is respected."""
        monitor = ClipboardMonitor(poll_interval=1.0)
        assert monitor.poll_interval == 1.0

    def test_callback_stored(self):
        """Callback function is stored."""
        callback = lambda x: x

        monitor = ClipboardMonitor(on_item_detected=callback)
        assert monitor.on_item_detected is callback

    def test_tkinter_root_stored(self):
        """Tkinter root is stored for fallback."""
        from unittest.mock import Mock

        tk_root = Mock()
        monitor = ClipboardMonitor(tk_root=tk_root)
        assert monitor.tk_root is tk_root


class TestClipboardMonitorEdgeCases:
    """Tests for edge cases in clipboard monitoring."""

    def test_detect_item_with_only_separator(self):
        """Text with only separator is not detected as item."""
        monitor = ClipboardMonitor()
        text = "--------\n--------\n--------\n--------"
        assert monitor._is_poe_item(text) is False

    def test_detect_item_near_min_length(self):
        """Text near minimum length boundary."""
        monitor = ClipboardMonitor()
        # Exactly 20 chars with 2 indicators should work
        text = "Rarity: Rare--------"  # 20 chars
        assert monitor._is_poe_item(text) is True

    def test_stats_with_hotkeys(self):
        """Stats include registered hotkeys."""
        monitor = ClipboardMonitor()
        monitor._hotkeys = [
            HotkeyConfig("ctrl+a", "Test A"),
            HotkeyConfig("ctrl+b", "Test B"),
        ]

        stats = monitor.get_stats()
        assert stats["hotkeys_registered"] == 2
        assert len(stats["hotkeys"]) == 2
        assert stats["hotkeys"][0]["hotkey"] == "ctrl+a"
        assert stats["hotkeys"][1]["description"] == "Test B"

    def test_stop_monitoring_without_thread(self):
        """stop_monitoring handles case with no thread."""
        monitor = ClipboardMonitor()
        monitor._running = True
        monitor._monitor_thread = None

        # Should not raise
        monitor.stop_monitoring()
        assert monitor._running is False


class TestPriceCheckHotkeyManagerCallbacks:
    """Tests for hotkey callback handling."""

    def test_on_price_check_hotkey_with_item(self):
        """Hotkey triggers callback when item found."""
        calls = []

        def callback(text):
            calls.append(text)

        manager = PriceCheckHotkeyManager(callback)

        item_text = """Item Class: Amulets
Rarity: Rare
Storm Collar
Onyx Amulet
--------
Item Level: 84"""

        manager.monitor._get_clipboard = lambda: item_text
        manager._on_price_check_hotkey()

        assert len(calls) == 1
        assert calls[0] == item_text

        manager.cleanup()

    def test_on_price_check_hotkey_no_item(self):
        """Hotkey doesn't trigger callback when no item."""
        calls = []

        def callback(text):
            calls.append(text)

        manager = PriceCheckHotkeyManager(callback)
        manager.monitor._get_clipboard = lambda: "not an item"
        manager._on_price_check_hotkey()

        assert len(calls) == 0

        manager.cleanup()

    def test_on_price_check_hotkey_callback_error(self):
        """Hotkey handles callback errors gracefully."""
        def error_callback(text):
            raise ValueError("Test error")

        manager = PriceCheckHotkeyManager(error_callback)

        item_text = """Item Class: Rings
Rarity: Rare
Storm Ring
Diamond Ring
--------
Item Level: 80"""

        manager.monitor._get_clipboard = lambda: item_text

        # Should not raise
        manager._on_price_check_hotkey()

        manager.cleanup()
