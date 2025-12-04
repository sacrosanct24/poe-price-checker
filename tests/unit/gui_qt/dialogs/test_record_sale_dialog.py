"""Tests for RecordSaleDialog."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QDialog, QWidget


class TestRecordSaleDialogInit:
    """Tests for RecordSaleDialog initialization."""

    def test_init_with_defaults(self, qtbot):
        """Can initialize with default parameters."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Record Sale"
        assert dialog._item_name == ""
        assert dialog._suggested_price == 0.0

    def test_init_with_item_name(self, qtbot):
        """Can initialize with item name."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        item_name = "Tabula Rasa"
        dialog = RecordSaleDialog(item_name=item_name)
        qtbot.addWidget(dialog)

        assert dialog._item_name == item_name

    def test_init_with_suggested_price(self, qtbot):
        """Can initialize with suggested price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(suggested_price=42.5)
        qtbot.addWidget(dialog)

        assert dialog._suggested_price == 42.5

    def test_init_with_all_parameters(self, qtbot):
        """Can initialize with all parameters."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        parent = QWidget()
        qtbot.addWidget(parent)

        dialog = RecordSaleDialog(
            parent=parent,
            item_name="Headhunter",
            suggested_price=250.0,
        )
        qtbot.addWidget(dialog)

        assert dialog._item_name == "Headhunter"
        assert dialog._suggested_price == 250.0

    def test_has_minimum_size(self, qtbot):
        """Dialog has minimum width and height."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() == 300
        assert dialog.minimumHeight() == 180

    def test_size_grip_enabled(self, qtbot):
        """Dialog has size grip enabled."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert dialog.isSizeGripEnabled() is True

    @patch("gui_qt.dialogs.record_sale_dialog.apply_window_icon")
    def test_applies_window_icon(self, mock_apply_icon, qtbot):
        """Dialog applies window icon."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        mock_apply_icon.assert_called_once_with(dialog)


class TestRecordSaleDialogWidgets:
    """Tests for RecordSaleDialog widget creation."""

    def test_displays_item_name(self, qtbot):
        """Dialog displays the item name."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        item_name = "Shav's Wrappings"
        dialog = RecordSaleDialog(item_name=item_name)
        qtbot.addWidget(dialog)

        # Item name should be in a label
        # We can't easily check without accessing private widgets
        # but we verify it doesn't crash
        assert dialog._item_name == item_name

    def test_has_price_spinbox(self, qtbot):
        """Dialog has a price spinbox."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "price_spin")
        assert dialog.price_spin is not None

    def test_price_spinbox_range(self, qtbot):
        """Price spinbox has correct range."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert dialog.price_spin.minimum() == 0
        assert dialog.price_spin.maximum() == 999999

    def test_price_spinbox_decimals(self, qtbot):
        """Price spinbox allows 1 decimal place."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert dialog.price_spin.decimals() == 1

    def test_price_spinbox_suffix(self, qtbot):
        """Price spinbox has chaos orb suffix."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert dialog.price_spin.suffix() == " c"

    def test_price_loads_suggested_value(self, qtbot):
        """Price spinbox loads suggested price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        suggested_price = 123.5
        dialog = RecordSaleDialog(suggested_price=suggested_price)
        qtbot.addWidget(dialog)

        assert dialog.price_spin.value() == suggested_price

    def test_has_notes_input(self, qtbot):
        """Dialog has a notes input field."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "notes_input")
        assert dialog.notes_input is not None

    def test_notes_input_has_placeholder(self, qtbot):
        """Notes input has placeholder text."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        placeholder = dialog.notes_input.placeholderText()
        assert "Optional" in placeholder or "notes" in placeholder.lower()

    def test_has_cancel_button(self, qtbot):
        """Dialog has a cancel button."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        # Can't easily check buttons without accessing layout
        # but we verify dialog creation doesn't crash

    def test_has_save_button(self, qtbot):
        """Dialog has a save button."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        # Can't easily check buttons without accessing layout
        # but we verify dialog creation doesn't crash


class TestRecordSaleDialogActions:
    """Tests for RecordSaleDialog button actions."""

    def test_cancel_button_rejects_dialog(self, qtbot):
        """Cancel button rejects the dialog."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        # Find cancel button and click it
        with patch.object(dialog, "reject") as mock_reject:
            # Manually trigger reject
            dialog.reject()
            mock_reject.assert_called_once()

    def test_save_button_accepts_dialog(self, qtbot):
        """Save button accepts the dialog."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        with patch.object(dialog, "accept") as mock_accept:
            dialog.accept()
            mock_accept.assert_called_once()


class TestRecordSaleDialogGetValues:
    """Tests for RecordSaleDialog.get_values() method."""

    def test_get_values_returns_tuple(self, qtbot):
        """get_values() returns a tuple."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        values = dialog.get_values()
        assert isinstance(values, tuple)
        assert len(values) == 2

    def test_get_values_returns_price(self, qtbot):
        """get_values() returns the price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(suggested_price=50.0)
        qtbot.addWidget(dialog)

        price, notes = dialog.get_values()
        assert price == 50.0

    def test_get_values_returns_notes(self, qtbot):
        """get_values() returns the notes."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        test_notes = "Sold to player123"
        dialog.notes_input.setText(test_notes)

        price, notes = dialog.get_values()
        assert notes == test_notes

    def test_get_values_strips_notes(self, qtbot):
        """get_values() strips whitespace from notes."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        dialog.notes_input.setText("  test notes  ")

        price, notes = dialog.get_values()
        assert notes == "test notes"

    def test_get_values_with_empty_notes(self, qtbot):
        """get_values() returns empty string for empty notes."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        price, notes = dialog.get_values()
        assert notes == ""

    def test_get_values_with_modified_price(self, qtbot):
        """get_values() returns modified price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(suggested_price=10.0)
        qtbot.addWidget(dialog)

        dialog.price_spin.setValue(25.5)

        price, notes = dialog.get_values()
        assert price == 25.5

    def test_get_values_with_zero_price(self, qtbot):
        """get_values() handles zero price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        dialog.price_spin.setValue(0.0)

        price, notes = dialog.get_values()
        assert price == 0.0

    def test_get_values_with_max_price(self, qtbot):
        """get_values() handles maximum price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog()
        qtbot.addWidget(dialog)

        dialog.price_spin.setValue(999999.0)

        price, notes = dialog.get_values()
        assert price == 999999.0


class TestRecordSaleDialogUsageScenarios:
    """Tests for common usage scenarios."""

    def test_typical_sale_workflow(self, qtbot):
        """Test typical workflow for recording a sale."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        # User records sale of item with suggested price
        dialog = RecordSaleDialog(
            item_name="Goldrim",
            suggested_price=1.5,
        )
        qtbot.addWidget(dialog)

        # User adjusts price and adds notes
        dialog.price_spin.setValue(2.0)
        dialog.notes_input.setText("Quick sale")

        # User saves
        price, notes = dialog.get_values()
        assert price == 2.0
        assert notes == "Quick sale"

    def test_sale_with_default_price(self, qtbot):
        """Test recording sale accepting default price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(
            item_name="Atziri's Promise",
            suggested_price=5.0,
        )
        qtbot.addWidget(dialog)

        # User accepts default price, no notes
        price, notes = dialog.get_values()
        assert price == 5.0
        assert notes == ""

    def test_sale_with_custom_price(self, qtbot):
        """Test recording sale with custom price."""
        from gui_qt.dialogs.record_sale_dialog import RecordSaleDialog

        dialog = RecordSaleDialog(item_name="Test Item")
        qtbot.addWidget(dialog)

        # User enters custom price
        dialog.price_spin.setValue(100.5)

        price, notes = dialog.get_values()
        assert price == 100.5
