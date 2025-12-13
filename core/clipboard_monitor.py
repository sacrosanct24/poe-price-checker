"""
Clipboard Monitor with Hotkey Support.

Provides background monitoring of clipboard changes and hotkey-triggered
item price checking for seamless PoE integration.

Supports:
- Automatic clipboard change detection
- Global hotkey bindings (e.g., Ctrl+Shift+C for price check)
- Thread-safe operation with main GUI
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# Optional dependencies - gracefully handle missing
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    logger.warning("keyboard module not available - hotkey support disabled")

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    logger.warning("pyperclip module not available - using tkinter clipboard")


@dataclass
class HotkeyConfig:
    """Configuration for a hotkey binding."""
    hotkey: str  # e.g., "ctrl+shift+c"
    description: str
    enabled: bool = True


class ClipboardMonitor:
    """
    Monitors clipboard for item text and provides hotkey support.

    Features:
    - Background thread monitors clipboard changes
    - Global hotkey bindings for quick price checks
    - Callbacks for item detection
    - PoE item text detection (filters non-item text)
    """

    # Patterns that indicate PoE item text
    POE_ITEM_INDICATORS = [
        "Rarity:",
        "Item Class:",
        "--------",
        "Item Level:",
    ]

    def __init__(
        self,
        on_item_detected: Optional[Callable[[str], None]] = None,
        poll_interval: float = 0.5,
        tk_root=None,
    ):
        """
        Initialize the clipboard monitor.

        Args:
            on_item_detected: Callback when PoE item is detected in clipboard
            poll_interval: Seconds between clipboard checks (default 0.5)
            tk_root: Tkinter root window (for clipboard access fallback)
        """
        self.on_item_detected = on_item_detected
        self.poll_interval = poll_interval
        self.tk_root = tk_root

        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_clipboard = ""
        self._hotkeys: List[HotkeyConfig] = []
        self._lock = threading.Lock()

        # Statistics
        self.items_detected = 0
        self.clipboard_reads = 0

    def _get_clipboard(self) -> str:
        """Get current clipboard text using available method."""
        self.clipboard_reads += 1

        if PYPERCLIP_AVAILABLE:
            try:
                val = pyperclip.paste()
                return str(val or "")
            except Exception as e:
                logger.debug(f"pyperclip.paste() failed: {e}")

        # Fallback to tkinter
        if self.tk_root:
            try:
                val2 = self.tk_root.clipboard_get()
                return str(val2 or "")
            except Exception as e:
                logger.debug(f"tkinter clipboard_get() failed: {e}")

        return ""

    # Maximum clipboard size to process (100KB should be more than enough for any PoE item)
    MAX_CLIPBOARD_SIZE = 100_000

    def _is_poe_item(self, text: str) -> bool:
        """
        Check if text looks like PoE item clipboard data.

        Args:
            text: Clipboard text to check

        Returns:
            True if text appears to be PoE item data
        """
        if not text or len(text) < 20:
            return False

        # Security: Reject suspiciously large clipboard content
        if len(text) > self.MAX_CLIPBOARD_SIZE:
            logger.warning(f"Clipboard content too large ({len(text)} bytes), ignoring")
            return False

        # Count matching indicators
        matches = sum(1 for indicator in self.POE_ITEM_INDICATORS if indicator in text)

        # Need at least 2 indicators for confidence
        return matches >= 2

    def _clipboard_poll_loop(self) -> None:
        """Background thread loop that polls clipboard for changes."""
        logger.info("Clipboard monitor started")

        while self._running:
            try:
                current = self._get_clipboard()

                # Keep critical section minimal: compute whether to notify and update state
                should_notify = False
                notify_payload = None
                with self._lock:
                    if current and current != self._last_clipboard:
                        self._last_clipboard = current

                        # Check if it's PoE item data
                        if self._is_poe_item(current):
                            self.items_detected += 1
                            should_notify = True
                            notify_payload = current

                # Perform logging and callbacks outside the lock to avoid deadlocks
                if should_notify and notify_payload is not None:
                    logger.info(f"PoE item detected in clipboard ({len(current)} chars)")
                    if self.on_item_detected:
                        try:
                            self.on_item_detected(notify_payload)
                        except Exception as e:
                            logger.error(f"Item callback error: {e}")

                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Clipboard poll error: {e}")
                time.sleep(1.0)  # Longer delay on error

        logger.info("Clipboard monitor stopped")

    def start_monitoring(self) -> bool:
        """
        Start background clipboard monitoring.

        Returns:
            True if started successfully
        """
        if self._running:
            logger.warning("Clipboard monitor already running")
            return False

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._clipboard_poll_loop,
            daemon=True,
            name="ClipboardMonitor",
        )
        self._monitor_thread.start()
        return True

    def stop_monitoring(self) -> None:
        """Stop background clipboard monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

    def register_hotkey(
        self,
        hotkey: str,
        callback: Callable[[], None],
        description: str = "",
    ) -> bool:
        """
        Register a global hotkey.

        Args:
            hotkey: Key combination (e.g., "ctrl+shift+c")
            callback: Function to call when hotkey pressed
            description: Human-readable description

        Returns:
            True if registered successfully
        """
        if not KEYBOARD_AVAILABLE:
            logger.warning(f"Cannot register hotkey '{hotkey}' - keyboard module not available")
            return False

        try:
            keyboard.add_hotkey(hotkey, callback, suppress=False)
            self._hotkeys.append(HotkeyConfig(hotkey, description))
            logger.info(f"Registered hotkey: {hotkey} ({description})")
            return True
        except Exception as e:
            logger.error(f"Failed to register hotkey '{hotkey}': {e}")
            return False

    def unregister_hotkey(self, hotkey: str) -> bool:
        """
        Unregister a hotkey.

        Args:
            hotkey: Key combination to unregister

        Returns:
            True if unregistered successfully
        """
        if not KEYBOARD_AVAILABLE:
            return False

        try:
            keyboard.remove_hotkey(hotkey)
            self._hotkeys = [h for h in self._hotkeys if h.hotkey != hotkey]
            logger.info(f"Unregistered hotkey: {hotkey}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister hotkey '{hotkey}': {e}")
            return False

    def unregister_all_hotkeys(self) -> None:
        """Unregister all registered hotkeys."""
        if not KEYBOARD_AVAILABLE:
            return

        for config in self._hotkeys:
            try:
                keyboard.remove_hotkey(config.hotkey)
            except Exception as e:
                logger.debug(f"Failed to remove hotkey '{config.hotkey}': {e}")
        self._hotkeys.clear()
        logger.info("Unregistered all hotkeys")

    def check_clipboard_now(self) -> Optional[str]:
        """
        Check clipboard immediately and return if PoE item.

        Returns:
            Item text if PoE item found, None otherwise
        """
        text = self._get_clipboard()
        if self._is_poe_item(text):
            return text
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "running": self._running,
            "items_detected": self.items_detected,
            "clipboard_reads": self.clipboard_reads,
            "hotkeys_registered": len(self._hotkeys),
            "hotkeys": [{"hotkey": h.hotkey, "description": h.description} for h in self._hotkeys],
        }

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_monitoring()
        self.unregister_all_hotkeys()


class PriceCheckHotkeyManager:
    """
    Convenience class for setting up common PoE price check hotkeys.

    Default hotkeys:
    - Ctrl+Shift+C: Check clipboard item price
    - Ctrl+Shift+V: Paste and check price
    """

    DEFAULT_PRICE_CHECK_HOTKEY = "ctrl+shift+c"
    DEFAULT_PASTE_CHECK_HOTKEY = "ctrl+shift+v"

    def __init__(
        self,
        price_check_callback: Callable[[str], None],
        tk_root=None,
    ):
        """
        Initialize the hotkey manager.

        Args:
            price_check_callback: Function to call with item text for pricing
            tk_root: Tkinter root for clipboard access
        """
        self.price_check_callback = price_check_callback
        self.monitor = ClipboardMonitor(
            on_item_detected=None,  # Manual trigger only
            tk_root=tk_root,
        )

    def setup_default_hotkeys(self) -> dict:
        """
        Set up default hotkeys for price checking.

        Returns:
            Dict with hotkey setup results
        """
        results = {}

        # Price check hotkey
        success = self.monitor.register_hotkey(
            self.DEFAULT_PRICE_CHECK_HOTKEY,
            self._on_price_check_hotkey,
            "Check clipboard item price",
        )
        results[self.DEFAULT_PRICE_CHECK_HOTKEY] = success

        return results

    def _on_price_check_hotkey(self) -> None:
        """Handle price check hotkey press."""
        item_text = self.monitor.check_clipboard_now()
        if item_text:
            logger.info("Price check hotkey triggered")
            try:
                self.price_check_callback(item_text)
            except Exception as e:
                logger.error(f"Price check callback error: {e}")
        else:
            logger.debug("No PoE item in clipboard")

    def enable_auto_detection(
        self,
        on_item_detected: Callable[[str], None],
    ) -> bool:
        """
        Enable automatic clipboard monitoring.

        Args:
            on_item_detected: Callback when item detected

        Returns:
            True if monitoring started
        """
        self.monitor.on_item_detected = on_item_detected
        return self.monitor.start_monitoring()

    def disable_auto_detection(self) -> None:
        """Disable automatic clipboard monitoring."""
        self.monitor.stop_monitoring()

    def cleanup(self) -> None:
        """Clean up all resources."""
        self.monitor.cleanup()


# Singleton instance for global access
_manager: Optional[PriceCheckHotkeyManager] = None


def get_hotkey_manager(
    price_check_callback: Optional[Callable[[str], None]] = None,
    tk_root=None,
) -> Optional[PriceCheckHotkeyManager]:
    """
    Get or create the global hotkey manager.

    Args:
        price_check_callback: Required on first call
        tk_root: Optional tkinter root

    Returns:
        PriceCheckHotkeyManager or None if not initialized
    """
    global _manager
    if _manager is None and price_check_callback:
        _manager = PriceCheckHotkeyManager(price_check_callback, tk_root)
    return _manager


def cleanup_hotkey_manager() -> None:
    """Clean up the global hotkey manager."""
    global _manager
    if _manager:
        _manager.cleanup()
        _manager = None


# Testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("CLIPBOARD MONITOR TEST")
    print("=" * 60)

    print(f"\nkeyboard module available: {KEYBOARD_AVAILABLE}")
    print(f"pyperclip module available: {PYPERCLIP_AVAILABLE}")

    # Test clipboard detection
    monitor = ClipboardMonitor()

    print("\nTesting clipboard access...")
    text = monitor._get_clipboard()
    print(f"  Current clipboard length: {len(text)} chars")

    # Test PoE item detection
    test_item = """Item Class: Body Armours
Rarity: Rare
Doom Shell
Vaal Regalia
--------
Item Level: 86
--------
+80 to maximum Life
+40% to Fire Resistance"""

    print("\nTesting PoE item detection...")
    is_poe = monitor._is_poe_item(test_item)
    print(f"  Test item detected as PoE item: {is_poe}")

    non_item = "This is just regular text"
    is_poe = monitor._is_poe_item(non_item)
    print(f"  Regular text detected as PoE item: {is_poe}")

    # Test hotkey registration
    if KEYBOARD_AVAILABLE:
        print("\nTesting hotkey registration...")

        def dummy_callback():
            print("Hotkey pressed!")

        success = monitor.register_hotkey("ctrl+shift+t", dummy_callback, "Test hotkey")
        print(f"  Registered test hotkey: {success}")

        if success:
            print("  Press Ctrl+Shift+T to test (Ctrl+C to exit)...")
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                pass
            monitor.unregister_hotkey("ctrl+shift+t")
    else:
        print("\nHotkey test skipped (keyboard module not available)")

    print("\n" + "=" * 60)
    print("Stats:", monitor.get_stats())
    monitor.cleanup()
