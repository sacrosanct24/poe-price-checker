from __future__ import annotations

import threading
import time
import pytest

from core.clipboard_monitor import ClipboardMonitor


pytestmark = pytest.mark.unit


def _poe_text() -> str:
    return (
        "Rarity: Unique\n"
        "Item Class: Jewel\n"
        "--------\n"
        "Item Level: 86\n"
        "Some other lines...\n"
    )


def test_is_poe_item_and_max_size_enforced():
    m = ClipboardMonitor()

    # Clearly not PoE item (too short)
    assert not m._is_poe_item("short")

    # Valid PoE-looking text
    assert m._is_poe_item(_poe_text())

    # Oversized clipboard content should be rejected
    giant = "Rarity:" + ("x" * (m.MAX_CLIPBOARD_SIZE + 10))
    assert not m._is_poe_item(giant)


def test_on_item_detected_callback_runs_outside_lock(monkeypatch):
    """
    The monitor must not hold its internal lock while invoking callbacks.
    We verify by attempting a non-blocking acquire of the internal lock
    from inside the callback; it should succeed immediately.
    """

    # Prepare a monitor with a deterministic clipboard source
    callback_called = threading.Event()
    lock_acquired_inside_callback = {"ok": False}

    m = ClipboardMonitor(on_item_detected=lambda text: None, poll_interval=0.01)

    def fake_get_clipboard_seq():
        # first call returns valid item, subsequent calls return empty to stop processing
        if not hasattr(fake_get_clipboard_seq, "done"):
            fake_get_clipboard_seq.done = True  # type: ignore[attr-defined]
            return _poe_text()
        return ""

    def cb(text: str):
        # Attempt to acquire the internal lock without blocking
        got = m._lock.acquire(timeout=0)
        if got:
            m._lock.release()
        lock_acquired_inside_callback["ok"] = got
        callback_called.set()

    m.on_item_detected = cb
    monkeypatch.setattr(m, "_get_clipboard", fake_get_clipboard_seq)

    try:
        assert m.start_monitoring() is True
        # Wait for callback to fire
        assert callback_called.wait(timeout=1.0), "callback did not fire"
        # The lock should NOT be held during callback
        assert lock_acquired_inside_callback["ok"], "callback ran while lock was held"
    finally:
        m.stop_monitoring()
        # Give the thread a brief moment to exit cleanly
        time.sleep(0.02)
