"""
Tests for PyQt6 PinnedItemsWidget.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


@pytest.fixture
def qapp():
    """Create a QApplication instance for testing."""
    from PyQt6.QtWidgets import QApplication

    # Check if an instance already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_config_dir(tmp_path):
    """Mock the config directory to use temp path."""
    with patch("core.config.get_config_dir") as mock:
        mock.return_value = tmp_path
        yield tmp_path


# ============================================================================
# PinnedItemWidget Tests
# ============================================================================


def test_pinned_item_widget_creation(qapp):
    """Test creating a PinnedItemWidget."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemWidget

    item_data = {"item_name": "Goldrim", "chaos_value": 5.0}
    widget = PinnedItemWidget(item_data)

    assert widget is not None
    assert widget.item_data == item_data


def test_pinned_item_widget_signals(qapp):
    """Test PinnedItemWidget has required signals."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemWidget

    item_data = {"item_name": "Goldrim", "chaos_value": 5.0}
    widget = PinnedItemWidget(item_data)

    assert hasattr(widget, "unpin_requested")
    assert hasattr(widget, "inspect_requested")


def test_pinned_item_widget_item_data_property(qapp):
    """Test item_data property returns correct data."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemWidget

    item_data = {"item_name": "Tabula Rasa", "chaos_value": 10.0, "source": "test"}
    widget = PinnedItemWidget(item_data)

    assert widget.item_data["item_name"] == "Tabula Rasa"
    assert widget.item_data["chaos_value"] == 10.0


# ============================================================================
# PinnedItemsWidget Tests
# ============================================================================


def test_pinned_items_widget_creation(qapp, mock_config_dir):
    """Test creating a PinnedItemsWidget."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    assert widget is not None
    assert widget.pinned_items == []


def test_pinned_items_widget_signals(qapp, mock_config_dir):
    """Test PinnedItemsWidget has required signals."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    assert hasattr(widget, "item_inspected")
    assert hasattr(widget, "items_changed")


def test_pinned_items_widget_pin_item(qapp, mock_config_dir):
    """Test pinning an item."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    item_data = {"item_name": "Goldrim", "chaos_value": 5.0}
    result = widget.pin_item(item_data)

    assert result is True
    assert len(widget.pinned_items) == 1
    assert widget.pinned_items[0]["item_name"] == "Goldrim"


def test_pinned_items_widget_pin_duplicate(qapp, mock_config_dir):
    """Test pinning duplicate item returns False."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    item_data = {"item_name": "Goldrim", "chaos_value": 5.0}
    widget.pin_item(item_data)

    # Try to pin same item again
    result = widget.pin_item({"item_name": "Goldrim", "chaos_value": 10.0})

    assert result is False
    assert len(widget.pinned_items) == 1


def test_pinned_items_widget_pin_items_batch(qapp, mock_config_dir):
    """Test pinning multiple items at once."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    items = [
        {"item_name": "Goldrim", "chaos_value": 5.0},
        {"item_name": "Tabula Rasa", "chaos_value": 10.0},
        {"item_name": "Wanderlust", "chaos_value": 1.0},
    ]

    count = widget.pin_items(items)

    assert count == 3
    assert len(widget.pinned_items) == 3


def test_pinned_items_widget_unpin_item(qapp, mock_config_dir):
    """Test unpinning an item."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    item_data = {"item_name": "Goldrim", "chaos_value": 5.0}
    widget.pin_item(item_data)

    result = widget.unpin_item(item_data)

    assert result is True
    assert len(widget.pinned_items) == 0


def test_pinned_items_widget_unpin_nonexistent(qapp, mock_config_dir):
    """Test unpinning item that doesn't exist returns False."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    result = widget.unpin_item({"item_name": "NonExistent"})

    assert result is False


def test_pinned_items_widget_clear_all(qapp, mock_config_dir):
    """Test clearing all pinned items."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    # Pin some items
    widget.pin_item({"item_name": "Item1", "chaos_value": 5.0})
    widget.pin_item({"item_name": "Item2", "chaos_value": 10.0})
    widget.pin_item({"item_name": "Item3", "chaos_value": 15.0})

    assert len(widget.pinned_items) == 3

    widget.clear_all()

    assert len(widget.pinned_items) == 0


def test_pinned_items_widget_is_pinned(qapp, mock_config_dir):
    """Test is_pinned method."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    widget.pin_item({"item_name": "Goldrim", "chaos_value": 5.0})

    assert widget.is_pinned("Goldrim") is True
    assert widget.is_pinned("Tabula Rasa") is False


def test_pinned_items_widget_max_limit(qapp, mock_config_dir):
    """Test max pinned items limit is enforced."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    # Pin up to max limit
    for i in range(widget.MAX_PINNED_ITEMS):
        result = widget.pin_item({"item_name": f"Item{i}", "chaos_value": float(i)})
        assert result is True

    # Try to pin one more
    result = widget.pin_item({"item_name": "OverLimit", "chaos_value": 999.0})

    assert result is False
    assert len(widget.pinned_items) == widget.MAX_PINNED_ITEMS


def test_pinned_items_widget_persistence_save(qapp, mock_config_dir):
    """Test pinned items are saved to file."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    widget.pin_item({"item_name": "Goldrim", "chaos_value": 5.0})
    widget.pin_item({"item_name": "Tabula Rasa", "chaos_value": 10.0})

    # Check file was created
    storage_file = mock_config_dir / "pinned_items.json"
    assert storage_file.exists()

    # Check contents
    with open(storage_file, "r") as f:
        data = json.load(f)

    assert len(data) == 2
    assert data[0]["item_name"] == "Goldrim"
    assert data[1]["item_name"] == "Tabula Rasa"


def test_pinned_items_widget_persistence_load(qapp, mock_config_dir):
    """Test pinned items are loaded from file on creation."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    # Create storage file with existing items
    storage_file = mock_config_dir / "pinned_items.json"
    existing_items = [
        {"item_name": "PreExisting1", "chaos_value": 100.0},
        {"item_name": "PreExisting2", "chaos_value": 200.0},
    ]
    with open(storage_file, "w") as f:
        json.dump(existing_items, f)

    # Create widget - should load existing items
    widget = PinnedItemsWidget()

    assert len(widget.pinned_items) == 2
    assert widget.is_pinned("PreExisting1")
    assert widget.is_pinned("PreExisting2")


def test_pinned_items_widget_items_changed_signal(qapp, mock_config_dir):
    """Test items_changed signal is emitted."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    received_items = []

    def on_items_changed(items):
        received_items.extend(items)

    widget.items_changed.connect(on_items_changed)

    widget.pin_item({"item_name": "Test", "chaos_value": 5.0})

    assert len(received_items) == 1
    assert received_items[0]["item_name"] == "Test"


def test_pinned_items_widget_pinned_items_copy(qapp, mock_config_dir):
    """Test pinned_items property returns a copy, not the original list."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    widget.pin_item({"item_name": "Test", "chaos_value": 5.0})

    items1 = widget.pinned_items
    items2 = widget.pinned_items

    # Should be different list objects
    assert items1 is not items2
    # But same content
    assert items1 == items2


def test_pinned_items_widget_serializable_data_only(qapp, mock_config_dir):
    """Test only serializable data is saved (no private keys or non-JSON types)."""
    from gui_qt.widgets.pinned_items_widget import PinnedItemsWidget

    widget = PinnedItemsWidget()

    # Include non-serializable data
    item_data = {
        "item_name": "Test",
        "chaos_value": 5.0,
        "_private": "should_not_save",
        "_item": object(),  # Non-serializable
    }

    widget.pin_item(item_data)

    # Check file contents
    storage_file = mock_config_dir / "pinned_items.json"
    with open(storage_file, "r") as f:
        data = json.load(f)

    # Private keys should be filtered out
    assert "_private" not in data[0]
    assert "_item" not in data[0]
    assert "item_name" in data[0]
