"""Tests for core/clipboard_monitor.py."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestHotkeyConfig:
    """Tests for HotkeyConfig dataclass."""

    def test_hotkey_config_creation(self):
        """Test creating a HotkeyConfig."""
        from core.clipboard_monitor import HotkeyConfig

        config = HotkeyConfig(
            hotkey="ctrl+shift+c",
            description="Test hotkey",
            enabled=True,
        )

        assert config.hotkey == "ctrl+shift+c"
        assert config.description == "Test hotkey"
        assert config.enabled is True

    def test_hotkey_config_defaults(self):
        """Test HotkeyConfig default values."""
        from core.clipboard_monitor import HotkeyConfig

        config = HotkeyConfig(hotkey="ctrl+c", description="Copy")

        assert config.enabled is True  # Default


class TestClipboardMonitor:
    """Tests for ClipboardMonitor class."""

    def test_init_default_values(self):
        """Test ClipboardMonitor initialization with defaults."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        assert monitor.on_item_detected is None
        assert monitor.poll_interval == 0.5
        assert monitor.tk_root is None
        assert monitor._running is False
        assert monitor._monitor_thread is None
        assert monitor._last_clipboard == ""
        assert monitor._hotkeys == []
        assert monitor.items_detected == 0
        assert monitor.clipboard_reads == 0

    def test_init_custom_values(self):
        """Test ClipboardMonitor with custom values."""
        from core.clipboard_monitor import ClipboardMonitor

        callback = MagicMock()
        tk_mock = MagicMock()

        monitor = ClipboardMonitor(
            on_item_detected=callback,
            poll_interval=1.0,
            tk_root=tk_mock,
        )

        assert monitor.on_item_detected is callback
        assert monitor.poll_interval == 1.0
        assert monitor.tk_root is tk_mock

    def test_poe_item_indicators(self):
        """Test POE_ITEM_INDICATORS constant."""
        from core.clipboard_monitor import ClipboardMonitor

        indicators = ClipboardMonitor.POE_ITEM_INDICATORS

        assert "Rarity:" in indicators
        assert "Item Class:" in indicators
        assert "--------" in indicators
        assert "Item Level:" in indicators

    def test_is_poe_item_valid(self):
        """Test _is_poe_item with valid PoE item text."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        item_text = """Item Class: Body Armours
Rarity: Rare
Doom Shell
Vaal Regalia
--------
Item Level: 86
--------
+80 to maximum Life"""

        assert monitor._is_poe_item(item_text) is True

    def test_is_poe_item_empty(self):
        """Test _is_poe_item with empty text."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        assert monitor._is_poe_item("") is False
        assert monitor._is_poe_item(None) is False

    def test_is_poe_item_short_text(self):
        """Test _is_poe_item with text too short."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        assert monitor._is_poe_item("short") is False
        assert monitor._is_poe_item("a" * 19) is False

    def test_is_poe_item_regular_text(self):
        """Test _is_poe_item with non-PoE text."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        assert monitor._is_poe_item("This is just some regular clipboard text that is long enough") is False

    def test_is_poe_item_only_one_indicator(self):
        """Test _is_poe_item needs at least 2 indicators."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        # Only one indicator - should not match
        text_with_one = "This text has Rarity: Rare but nothing else special here"
        assert monitor._is_poe_item(text_with_one) is False

    def test_is_poe_item_too_large(self):
        """Test _is_poe_item rejects oversized content."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        # Create text larger than MAX_CLIPBOARD_SIZE
        large_text = "Rarity: Rare\n--------\nItem Level: 86\n" + "x" * 150000

        assert monitor._is_poe_item(large_text) is False

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_get_clipboard_with_pyperclip(self, mock_pyperclip):
        """Test _get_clipboard using pyperclip."""
        from core.clipboard_monitor import ClipboardMonitor

        mock_pyperclip.paste.return_value = "test clipboard content"

        monitor = ClipboardMonitor()
        result = monitor._get_clipboard()

        assert result == "test clipboard content"
        assert monitor.clipboard_reads == 1

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_get_clipboard_pyperclip_returns_none(self, mock_pyperclip):
        """Test _get_clipboard when pyperclip returns None."""
        from core.clipboard_monitor import ClipboardMonitor

        mock_pyperclip.paste.return_value = None

        monitor = ClipboardMonitor()
        result = monitor._get_clipboard()

        assert result == ""

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_get_clipboard_pyperclip_error_fallback_tkinter(self, mock_pyperclip):
        """Test _get_clipboard falls back to tkinter on pyperclip error."""
        from core.clipboard_monitor import ClipboardMonitor

        mock_pyperclip.paste.side_effect = Exception("pyperclip error")

        tk_mock = MagicMock()
        tk_mock.clipboard_get.return_value = "tkinter content"

        monitor = ClipboardMonitor(tk_root=tk_mock)
        result = monitor._get_clipboard()

        assert result == "tkinter content"

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', False)
    def test_get_clipboard_tkinter_only(self):
        """Test _get_clipboard using only tkinter."""
        from core.clipboard_monitor import ClipboardMonitor

        tk_mock = MagicMock()
        tk_mock.clipboard_get.return_value = "tkinter content"

        monitor = ClipboardMonitor(tk_root=tk_mock)
        result = monitor._get_clipboard()

        assert result == "tkinter content"

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', False)
    def test_get_clipboard_no_method_available(self):
        """Test _get_clipboard when no method is available."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor(tk_root=None)
        result = monitor._get_clipboard()

        assert result == ""

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', False)
    def test_get_clipboard_tkinter_error(self):
        """Test _get_clipboard handles tkinter errors."""
        from core.clipboard_monitor import ClipboardMonitor

        tk_mock = MagicMock()
        tk_mock.clipboard_get.side_effect = Exception("tkinter error")

        monitor = ClipboardMonitor(tk_root=tk_mock)
        result = monitor._get_clipboard()

        assert result == ""

    def test_start_monitoring(self):
        """Test starting the clipboard monitor."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor(poll_interval=0.1)

        result = monitor.start_monitoring()

        assert result is True
        assert monitor._running is True
        assert monitor._monitor_thread is not None
        assert monitor._monitor_thread.is_alive()

        # Cleanup
        monitor.stop_monitoring()

    def test_start_monitoring_already_running(self):
        """Test start_monitoring when already running."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor(poll_interval=0.1)
        monitor.start_monitoring()

        # Try to start again
        result = monitor.start_monitoring()

        assert result is False  # Already running

        # Cleanup
        monitor.stop_monitoring()

    def test_stop_monitoring(self):
        """Test stopping the clipboard monitor."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor(poll_interval=0.1)
        monitor.start_monitoring()

        # Give thread time to start
        time.sleep(0.1)

        monitor.stop_monitoring()

        assert monitor._running is False
        assert monitor._monitor_thread is None

    def test_stop_monitoring_not_running(self):
        """Test stop_monitoring when not running."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        # Should not raise
        monitor.stop_monitoring()

        assert monitor._running is False

    def test_is_running_property(self):
        """Test is_running property."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        assert monitor.is_running is False

        monitor._running = True
        assert monitor.is_running is True

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_check_clipboard_now_poe_item(self, mock_pyperclip):
        """Test check_clipboard_now with PoE item."""
        from core.clipboard_monitor import ClipboardMonitor

        item_text = """Item Class: Boots
Rarity: Rare
Test Boots
--------
Item Level: 75"""

        mock_pyperclip.paste.return_value = item_text

        monitor = ClipboardMonitor()
        result = monitor.check_clipboard_now()

        assert result == item_text

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_check_clipboard_now_not_poe_item(self, mock_pyperclip):
        """Test check_clipboard_now with non-PoE text."""
        from core.clipboard_monitor import ClipboardMonitor

        mock_pyperclip.paste.return_value = "regular text"

        monitor = ClipboardMonitor()
        result = monitor.check_clipboard_now()

        assert result is None

    def test_get_stats(self):
        """Test get_stats returns correct data."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()
        monitor.items_detected = 5
        monitor.clipboard_reads = 100
        monitor._running = True

        stats = monitor.get_stats()

        assert stats["running"] is True
        assert stats["items_detected"] == 5
        assert stats["clipboard_reads"] == 100
        assert stats["hotkeys_registered"] == 0
        assert stats["hotkeys"] == []

    def test_cleanup(self):
        """Test cleanup stops monitoring and unregisters hotkeys."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor(poll_interval=0.1)
        monitor.start_monitoring()

        monitor.cleanup()

        assert monitor._running is False
        assert monitor._hotkeys == []

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_clipboard_poll_loop_detects_item(self, mock_pyperclip):
        """Test clipboard poll loop detects PoE items."""
        from core.clipboard_monitor import ClipboardMonitor

        item_text = """Item Class: Amulet
Rarity: Rare
Test Amulet
--------
Item Level: 80"""

        callback = MagicMock()
        mock_pyperclip.paste.return_value = item_text

        monitor = ClipboardMonitor(
            on_item_detected=callback,
            poll_interval=0.05,
        )
        monitor.start_monitoring()

        # Wait for detection
        time.sleep(0.2)

        monitor.stop_monitoring()

        assert monitor.items_detected >= 1
        callback.assert_called()

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_clipboard_poll_loop_ignores_same_content(self, mock_pyperclip):
        """Test poll loop doesn't re-detect same content."""
        from core.clipboard_monitor import ClipboardMonitor

        item_text = """Item Class: Ring
Rarity: Rare
Test Ring
--------
Item Level: 75"""

        callback = MagicMock()
        mock_pyperclip.paste.return_value = item_text

        monitor = ClipboardMonitor(
            on_item_detected=callback,
            poll_interval=0.05,
        )
        monitor.start_monitoring()

        # Wait for multiple polls
        time.sleep(0.3)

        monitor.stop_monitoring()

        # Should only detect once (same content)
        assert callback.call_count == 1

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_clipboard_poll_loop_handles_callback_error(self, mock_pyperclip):
        """Test poll loop handles callback errors gracefully."""
        from core.clipboard_monitor import ClipboardMonitor

        item_text = """Item Class: Belt
Rarity: Rare
Test Belt
--------
Item Level: 70"""

        callback = MagicMock(side_effect=Exception("Callback error"))
        mock_pyperclip.paste.return_value = item_text

        monitor = ClipboardMonitor(
            on_item_detected=callback,
            poll_interval=0.05,
        )

        # Should not raise despite callback error
        monitor.start_monitoring()
        time.sleep(0.15)
        monitor.stop_monitoring()

        # Monitor should have continued running
        assert monitor.items_detected >= 1


class TestClipboardMonitorHotkeys:
    """Tests for hotkey functionality."""

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', True)
    @patch('core.clipboard_monitor.keyboard')
    def test_register_hotkey_success(self, mock_keyboard):
        """Test successful hotkey registration."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()
        callback = MagicMock()

        result = monitor.register_hotkey(
            "ctrl+shift+p",
            callback,
            "Price check",
        )

        assert result is True
        assert len(monitor._hotkeys) == 1
        assert monitor._hotkeys[0].hotkey == "ctrl+shift+p"
        assert monitor._hotkeys[0].description == "Price check"
        mock_keyboard.add_hotkey.assert_called_once()

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', False)
    def test_register_hotkey_keyboard_unavailable(self):
        """Test register_hotkey when keyboard module unavailable."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()
        callback = MagicMock()

        result = monitor.register_hotkey(
            "ctrl+shift+p",
            callback,
            "Price check",
        )

        assert result is False
        assert len(monitor._hotkeys) == 0

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', True)
    @patch('core.clipboard_monitor.keyboard')
    def test_register_hotkey_error(self, mock_keyboard):
        """Test register_hotkey handles errors."""
        from core.clipboard_monitor import ClipboardMonitor

        mock_keyboard.add_hotkey.side_effect = Exception("Registration failed")

        monitor = ClipboardMonitor()
        callback = MagicMock()

        result = monitor.register_hotkey(
            "invalid+key",
            callback,
            "Test",
        )

        assert result is False
        assert len(monitor._hotkeys) == 0

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', True)
    @patch('core.clipboard_monitor.keyboard')
    def test_unregister_hotkey_success(self, mock_keyboard):
        """Test successful hotkey unregistration."""
        from core.clipboard_monitor import ClipboardMonitor, HotkeyConfig

        monitor = ClipboardMonitor()
        monitor._hotkeys.append(HotkeyConfig("ctrl+a", "Test"))

        result = monitor.unregister_hotkey("ctrl+a")

        assert result is True
        assert len(monitor._hotkeys) == 0
        mock_keyboard.remove_hotkey.assert_called_once_with("ctrl+a")

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', False)
    def test_unregister_hotkey_keyboard_unavailable(self):
        """Test unregister_hotkey when keyboard module unavailable."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        result = monitor.unregister_hotkey("ctrl+a")

        assert result is False

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', True)
    @patch('core.clipboard_monitor.keyboard')
    def test_unregister_hotkey_error(self, mock_keyboard):
        """Test unregister_hotkey handles errors."""
        from core.clipboard_monitor import ClipboardMonitor, HotkeyConfig

        mock_keyboard.remove_hotkey.side_effect = Exception("Removal failed")

        monitor = ClipboardMonitor()
        monitor._hotkeys.append(HotkeyConfig("ctrl+a", "Test"))

        result = monitor.unregister_hotkey("ctrl+a")

        assert result is False

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', True)
    @patch('core.clipboard_monitor.keyboard')
    def test_unregister_all_hotkeys(self, mock_keyboard):
        """Test unregistering all hotkeys."""
        from core.clipboard_monitor import ClipboardMonitor, HotkeyConfig

        monitor = ClipboardMonitor()
        monitor._hotkeys = [
            HotkeyConfig("ctrl+a", "Test 1"),
            HotkeyConfig("ctrl+b", "Test 2"),
        ]

        monitor.unregister_all_hotkeys()

        assert len(monitor._hotkeys) == 0
        assert mock_keyboard.remove_hotkey.call_count == 2

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', False)
    def test_unregister_all_hotkeys_keyboard_unavailable(self):
        """Test unregister_all_hotkeys when keyboard unavailable."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor()

        # Should not raise
        monitor.unregister_all_hotkeys()

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', True)
    @patch('core.clipboard_monitor.keyboard')
    def test_unregister_all_hotkeys_handles_errors(self, mock_keyboard):
        """Test unregister_all handles individual errors."""
        from core.clipboard_monitor import ClipboardMonitor, HotkeyConfig

        mock_keyboard.remove_hotkey.side_effect = Exception("Error")

        monitor = ClipboardMonitor()
        monitor._hotkeys = [HotkeyConfig("ctrl+a", "Test")]

        # Should not raise
        monitor.unregister_all_hotkeys()
        assert len(monitor._hotkeys) == 0


class TestPriceCheckHotkeyManager:
    """Tests for PriceCheckHotkeyManager class."""

    def test_init(self):
        """Test PriceCheckHotkeyManager initialization."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        callback = MagicMock()

        manager = PriceCheckHotkeyManager(
            price_check_callback=callback,
            tk_root=None,
        )

        assert manager.price_check_callback is callback
        assert manager.monitor is not None

    def test_default_hotkeys(self):
        """Test default hotkey constants."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        assert PriceCheckHotkeyManager.DEFAULT_PRICE_CHECK_HOTKEY == "ctrl+shift+c"
        assert PriceCheckHotkeyManager.DEFAULT_PASTE_CHECK_HOTKEY == "ctrl+shift+v"

    @patch('core.clipboard_monitor.KEYBOARD_AVAILABLE', True)
    @patch('core.clipboard_monitor.keyboard')
    def test_setup_default_hotkeys(self, mock_keyboard):
        """Test setting up default hotkeys."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        callback = MagicMock()
        manager = PriceCheckHotkeyManager(callback)

        results = manager.setup_default_hotkeys()

        assert "ctrl+shift+c" in results
        assert results["ctrl+shift+c"] is True

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_on_price_check_hotkey_with_item(self, mock_pyperclip):
        """Test hotkey handler with PoE item in clipboard."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        item_text = """Item Class: Helmet
Rarity: Rare
Test Helm
--------
Item Level: 80"""

        mock_pyperclip.paste.return_value = item_text
        callback = MagicMock()

        manager = PriceCheckHotkeyManager(callback)
        manager._on_price_check_hotkey()

        callback.assert_called_once_with(item_text)

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_on_price_check_hotkey_no_item(self, mock_pyperclip):
        """Test hotkey handler with no PoE item."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        mock_pyperclip.paste.return_value = "not a poe item"
        callback = MagicMock()

        manager = PriceCheckHotkeyManager(callback)
        manager._on_price_check_hotkey()

        callback.assert_not_called()

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_on_price_check_hotkey_callback_error(self, mock_pyperclip):
        """Test hotkey handler catches callback errors."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        item_text = """Item Class: Gloves
Rarity: Rare
Test Gloves
--------
Item Level: 75"""

        mock_pyperclip.paste.return_value = item_text
        callback = MagicMock(side_effect=Exception("Callback error"))

        manager = PriceCheckHotkeyManager(callback)

        # Should not raise
        manager._on_price_check_hotkey()

    def test_enable_auto_detection(self):
        """Test enabling auto detection."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        callback = MagicMock()
        detection_callback = MagicMock()

        manager = PriceCheckHotkeyManager(callback)
        result = manager.enable_auto_detection(detection_callback)

        assert result is True
        assert manager.monitor.on_item_detected is detection_callback
        assert manager.monitor._running is True

        # Cleanup
        manager.cleanup()

    def test_disable_auto_detection(self):
        """Test disabling auto detection."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        callback = MagicMock()
        manager = PriceCheckHotkeyManager(callback)
        manager.monitor.start_monitoring()

        manager.disable_auto_detection()

        assert manager.monitor._running is False

    def test_cleanup(self):
        """Test cleanup."""
        from core.clipboard_monitor import PriceCheckHotkeyManager

        callback = MagicMock()
        manager = PriceCheckHotkeyManager(callback)
        manager.monitor.start_monitoring()

        manager.cleanup()

        assert manager.monitor._running is False


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_hotkey_manager_first_call(self):
        """Test get_hotkey_manager creates manager on first call."""
        from core.clipboard_monitor import (
            get_hotkey_manager,
            cleanup_hotkey_manager,
        )

        # Cleanup any existing manager
        cleanup_hotkey_manager()

        callback = MagicMock()
        manager = get_hotkey_manager(callback)

        assert manager is not None
        assert manager.price_check_callback is callback

        # Cleanup
        cleanup_hotkey_manager()

    def test_get_hotkey_manager_returns_same_instance(self):
        """Test get_hotkey_manager returns singleton."""
        from core.clipboard_monitor import (
            get_hotkey_manager,
            cleanup_hotkey_manager,
        )

        cleanup_hotkey_manager()

        callback = MagicMock()
        manager1 = get_hotkey_manager(callback)
        manager2 = get_hotkey_manager()

        assert manager1 is manager2

        cleanup_hotkey_manager()

    def test_get_hotkey_manager_no_callback_no_manager(self):
        """Test get_hotkey_manager returns None without callback on first call."""
        from core.clipboard_monitor import (
            get_hotkey_manager,
            cleanup_hotkey_manager,
        )

        cleanup_hotkey_manager()

        manager = get_hotkey_manager()

        assert manager is None

    def test_cleanup_hotkey_manager(self):
        """Test cleanup_hotkey_manager clears singleton."""
        from core.clipboard_monitor import (
            get_hotkey_manager,
            cleanup_hotkey_manager,
            _manager,
        )

        callback = MagicMock()
        get_hotkey_manager(callback)

        cleanup_hotkey_manager()

        # Next call without callback should return None
        manager = get_hotkey_manager()
        assert manager is None

    def test_cleanup_hotkey_manager_no_manager(self):
        """Test cleanup_hotkey_manager when no manager exists."""
        from core.clipboard_monitor import cleanup_hotkey_manager

        # Should not raise
        cleanup_hotkey_manager()


class TestClipboardMonitorThreadSafety:
    """Tests for thread safety of ClipboardMonitor."""

    @patch('core.clipboard_monitor.PYPERCLIP_AVAILABLE', True)
    @patch('core.clipboard_monitor.pyperclip')
    def test_concurrent_clipboard_reads(self, mock_pyperclip):
        """Test multiple threads can read clipboard safely."""
        from core.clipboard_monitor import ClipboardMonitor

        mock_pyperclip.paste.return_value = "test"

        monitor = ClipboardMonitor()
        results = []

        def read_clipboard():
            for _ in range(10):
                results.append(monitor._get_clipboard())

        threads = [threading.Thread(target=read_clipboard) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 50
        assert all(r == "test" for r in results)

    def test_start_stop_from_multiple_threads(self):
        """Test start/stop can be called from multiple threads."""
        from core.clipboard_monitor import ClipboardMonitor

        monitor = ClipboardMonitor(poll_interval=0.1)

        def toggle_monitor():
            monitor.start_monitoring()
            time.sleep(0.05)
            monitor.stop_monitoring()

        threads = [threading.Thread(target=toggle_monitor) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Final state should be stopped
        monitor.stop_monitoring()
        assert monitor._running is False
