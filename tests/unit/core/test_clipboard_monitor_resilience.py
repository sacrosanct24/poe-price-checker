from __future__ import annotations

import types
import pytest

from core.clipboard_monitor import ClipboardMonitor


pytestmark = pytest.mark.unit


def test_get_clipboard_handles_pyperclip_failure(monkeypatch):
    """
    If pyperclip.paste() raises, _get_clipboard should catch and return ""
    without crashing the monitor loop.
    """
    m = ClipboardMonitor()

    # Force the module to think pyperclip is available and inject a stub that raises
    monkeypatch.setattr("core.clipboard_monitor.PYPERCLIP_AVAILABLE", True, raising=False)
    stub = types.SimpleNamespace()

    def boom():
        raise RuntimeError("paste failed")

    stub.paste = boom
    monkeypatch.setattr("core.clipboard_monitor.pyperclip", stub, raising=False)

    # Should swallow the error and return empty string
    assert m._get_clipboard() == ""


def test_register_hotkey_returns_false_when_keyboard_unavailable(monkeypatch):
    """
    When the keyboard module isn't available, register_hotkey should be a no-op
    and return False with a warning (logging tested elsewhere).
    """
    m = ClipboardMonitor()
    # Simulate no keyboard module at runtime
    monkeypatch.setattr("core.clipboard_monitor.KEYBOARD_AVAILABLE", False, raising=False)
    assert m.register_hotkey("ctrl+shift+c", lambda: None, description="test") is False
