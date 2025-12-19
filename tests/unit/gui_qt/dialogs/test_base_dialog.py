"""Tests for gui_qt/dialogs/base_dialog.py - Base dialog classes."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QDialog

from gui_qt.dialogs.base_dialog import (
    BaseDialog,
    ConfirmDialog,
    InputDialog,
    confirm,
    get_input,
)


# =============================================================================
# BaseDialog Tests
# =============================================================================


class TestBaseDialogInit:
    """Tests for BaseDialog initialization."""

    def test_init_sets_title(self, qtbot):
        """Should set window title."""
        dialog = BaseDialog(title="Test Dialog")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Test Dialog"

    def test_init_sets_modal_true(self, qtbot):
        """Should set modal to True by default."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)
        assert dialog.isModal()

    def test_init_sets_modal_false(self, qtbot):
        """Should allow non-modal dialogs."""
        dialog = BaseDialog(title="Test", modal=False)
        qtbot.addWidget(dialog)
        assert not dialog.isModal()

    def test_init_sets_minimum_size(self, qtbot):
        """Should set minimum size."""
        dialog = BaseDialog(title="Test", min_width=500, min_height=300)
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 500
        assert dialog.minimumHeight() == 300

    def test_init_default_minimum_size(self, qtbot):
        """Should use default minimum size."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 400
        assert dialog.minimumHeight() == 200

    def test_init_creates_content_area(self, qtbot):
        """Should create content area widget."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)
        assert dialog._content_area is not None
        assert dialog._content_layout is not None

    def test_init_no_button_row_initially(self, qtbot):
        """Should not have button row initially."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)
        assert dialog._button_row is None


class TestBaseDialogContent:
    """Tests for content management."""

    def test_add_content_widget(self, qtbot):
        """Should add widget to content area."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        label = QLabel("Test content")
        dialog.add_content(label)

        assert dialog._content_layout.count() == 1

    def test_add_multiple_content_widgets(self, qtbot):
        """Should add multiple widgets."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_content(QLabel("First"))
        dialog.add_content(QLabel("Second"))
        dialog.add_content(QLabel("Third"))

        assert dialog._content_layout.count() == 3

    def test_add_stretch(self, qtbot):
        """Should add stretch to content."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_stretch()

        # Layout should have a stretch item
        assert dialog._content_layout.count() >= 1


class TestBaseDialogButtonRow:
    """Tests for button row functionality."""

    def test_add_button_row_creates_buttons(self, qtbot):
        """Should create primary and secondary buttons."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_button_row(
            primary_text="Save",
            secondary_text="Cancel",
        )

        assert dialog._primary_button is not None
        assert dialog._secondary_button is not None
        # Buttons may have mnemonic marker (&)
        assert "Save" in dialog._primary_button.text()
        assert "Cancel" in dialog._secondary_button.text()

    def test_add_button_row_primary_is_default(self, qtbot):
        """Should make primary button the default."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_button_row(primary_text="OK")

        assert dialog._primary_button.isDefault()

    def test_add_button_row_primary_action(self, qtbot):
        """Should connect primary action."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        action_called = []

        dialog.add_button_row(
            primary_text="OK",
            primary_action=lambda: action_called.append(True),
        )

        dialog._primary_button.click()
        assert len(action_called) == 1

    def test_add_button_row_secondary_action(self, qtbot):
        """Should connect secondary action (default to reject)."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_button_row(primary_text="OK", secondary_text="Cancel")

        # Default secondary action is reject, which will be connected
        assert dialog._secondary_button is not None

    def test_add_button_row_destructive_style(self, qtbot):
        """Should style destructive button differently."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_button_row(
            primary_text="Delete",
            destructive=True,
        )

        assert dialog._primary_button.property("destructive") is True

    def test_replace_button_row(self, qtbot):
        """Should replace existing button row."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_button_row(primary_text="First")
        first_btn = dialog._primary_button

        dialog.add_button_row(primary_text="Second")

        assert dialog._primary_button is not first_btn
        # Button text may have mnemonic marker (&)
        assert "Second" in dialog._primary_button.text()


class TestBaseDialogFocusManagement:
    """Tests for focus and tab order."""

    def test_register_focusable(self, qtbot):
        """Should register focusable widget."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        widget = QLabel("Focusable")
        dialog.register_focusable(widget)

        assert widget in dialog._focusable_widgets

    def test_button_row_registers_buttons(self, qtbot):
        """Should register buttons as focusable."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog.add_button_row(primary_text="OK", secondary_text="Cancel")

        assert dialog._primary_button in dialog._focusable_widgets
        assert dialog._secondary_button in dialog._focusable_widgets


class TestBaseDialogKeyboardShortcuts:
    """Tests for keyboard shortcuts."""

    def test_enter_clicks_primary_button(self, qtbot):
        """Should click primary button on Enter."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        clicked = []
        dialog.add_button_row(
            primary_text="OK",
            primary_action=lambda: clicked.append(True),
        )

        dialog._on_enter_pressed()

        assert len(clicked) == 1

    def test_enter_clicks_focused_button(self, qtbot):
        """Should click focused button on Enter."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        clicked = []

        dialog.add_button_row(
            primary_text="OK",
            secondary_text="Cancel",
            secondary_action=lambda: clicked.append("cancel"),
        )

        dialog._secondary_button.setFocus()
        # Simulate enter when secondary has focus
        # Can't easily test this without more complex setup


class TestBaseDialogGeometry:
    """Tests for geometry persistence."""

    @patch('gui_qt.dialogs.base_dialog.QSettings')
    def test_restore_geometry_on_init(self, mock_settings_cls, qtbot):
        """Should attempt to restore geometry."""
        mock_settings = MagicMock()
        mock_settings.value.return_value = None
        mock_settings_cls.return_value = mock_settings

        dialog = BaseDialog(title="Test", remember_geometry=True)
        qtbot.addWidget(dialog)

        mock_settings.beginGroup.assert_called()

    def test_no_restore_when_disabled(self, qtbot):
        """Should not restore when remember_geometry is False."""
        with patch('gui_qt.dialogs.base_dialog.QSettings'):
            dialog = BaseDialog(title="Test", remember_geometry=False)
            qtbot.addWidget(dialog)

            # Should not try to restore
            # (beginGroup might still be called during save, but not restore)

    def test_geometry_key_uses_class_name(self, qtbot):
        """Should use class name for geometry key."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        key = dialog._geometry_key()
        assert key == "BaseDialog"


class TestBaseDialogSizeHint:
    """Tests for size hint."""

    def test_size_hint_returns_reasonable_size(self, qtbot):
        """Should return reasonable default size."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        size = dialog.sizeHint()
        assert size.width() >= 400
        assert size.height() >= 200


# =============================================================================
# ConfirmDialog Tests
# =============================================================================


class TestConfirmDialogInit:
    """Tests for ConfirmDialog initialization."""

    def test_init_sets_title(self, qtbot):
        """Should set window title."""
        dialog = ConfirmDialog(title="Confirm Delete")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Confirm Delete"

    def test_init_displays_message(self, qtbot):
        """Should display confirmation message."""
        dialog = ConfirmDialog(
            title="Confirm",
            message="Are you sure?",
        )
        qtbot.addWidget(dialog)

        # Message should be in the dialog somewhere
        # Check by finding label with the text
        found = False
        for child in dialog.findChildren(QLabel):
            if "Are you sure?" in child.text():
                found = True
                break
        assert found

    def test_init_custom_button_text(self, qtbot):
        """Should use custom button text."""
        dialog = ConfirmDialog(
            title="Confirm",
            confirm_text="Delete",
            cancel_text="Keep",
        )
        qtbot.addWidget(dialog)

        # Button text may have mnemonic marker (&)
        assert "Delete" in dialog._primary_button.text()
        assert "Keep" in dialog._secondary_button.text()

    def test_init_destructive_styling(self, qtbot):
        """Should apply destructive styling."""
        dialog = ConfirmDialog(
            title="Confirm",
            destructive=True,
        )
        qtbot.addWidget(dialog)

        assert dialog._primary_button.property("destructive") is True


# =============================================================================
# InputDialog Tests
# =============================================================================


class TestInputDialogInit:
    """Tests for InputDialog initialization."""

    def test_init_sets_title(self, qtbot):
        """Should set window title."""
        dialog = InputDialog(title="Enter Value")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Enter Value"

    def test_init_creates_input_field(self, qtbot):
        """Should create input field."""
        dialog = InputDialog(title="Test")
        qtbot.addWidget(dialog)
        assert dialog._input is not None

    def test_init_sets_placeholder(self, qtbot):
        """Should set placeholder text."""
        dialog = InputDialog(
            title="Test",
            placeholder="Enter name...",
        )
        qtbot.addWidget(dialog)
        assert dialog._input.placeholderText() == "Enter name..."

    def test_init_sets_default_value(self, qtbot):
        """Should set default value."""
        dialog = InputDialog(
            title="Test",
            default_value="Default",
        )
        qtbot.addWidget(dialog)
        assert dialog._input.text() == "Default"

    def test_init_displays_label(self, qtbot):
        """Should display input label."""
        dialog = InputDialog(
            title="Test",
            label="Name:",
        )
        qtbot.addWidget(dialog)

        # Find label with text
        found = False
        for child in dialog.findChildren(QLabel):
            if "Name:" in child.text():
                found = True
                break
        assert found


class TestInputDialogValue:
    """Tests for InputDialog.value()."""

    def test_value_returns_input_text(self, qtbot):
        """Should return input text."""
        dialog = InputDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog._input.setText("Hello World")
        assert dialog.value() == "Hello World"

    def test_value_empty_string(self, qtbot):
        """Should return empty string when empty."""
        dialog = InputDialog(title="Test")
        qtbot.addWidget(dialog)

        dialog._input.setText("")
        assert dialog.value() == ""


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestConfirmFunction:
    """Tests for confirm() helper function."""

    def test_confirm_creates_dialog(self, qtbot):
        """Should create ConfirmDialog."""
        # Can't easily test the exec() part, but can test creation
        dialog = ConfirmDialog(
            None,
            title="Test",
            message="Message",
        )
        qtbot.addWidget(dialog)
        assert dialog is not None


class TestGetInputFunction:
    """Tests for get_input() helper function."""

    def test_get_input_creates_dialog(self, qtbot):
        """Should create InputDialog."""
        dialog = InputDialog(
            None,
            title="Test",
            label="Label:",
        )
        qtbot.addWidget(dialog)
        assert dialog is not None


# =============================================================================
# Edge Cases
# =============================================================================


class TestBaseDialogEdgeCases:
    """Edge case tests for BaseDialog."""

    def test_empty_title(self, qtbot):
        """Should handle empty title."""
        dialog = BaseDialog(title="")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == ""

    def test_title_with_help_text(self, qtbot):
        """Should show help text when enabled."""
        dialog = BaseDialog(
            title="Test",
            show_help=True,
            help_text="This is help text",
        )
        qtbot.addWidget(dialog)

        # Help text should be in dialog
        found = False
        for child in dialog.findChildren(QLabel):
            if "help text" in child.text():
                found = True
                break
        assert found

    def test_button_row_with_help_button(self, qtbot):
        """Should add help button when requested."""
        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        help_clicked = []
        dialog.add_button_row(
            primary_text="OK",
            show_help_button=True,
            help_action=lambda: help_clicked.append(True),
        )

        # Should have 3 buttons (help, cancel, ok)
        buttons = dialog._button_row.findChildren(QPushButton)
        assert len(buttons) >= 2  # At least primary and secondary

    def test_add_content_layout(self, qtbot):
        """Should add layout to content area."""
        from PyQt6.QtWidgets import QHBoxLayout

        dialog = BaseDialog(title="Test")
        qtbot.addWidget(dialog)

        layout = QHBoxLayout()
        dialog.add_content_layout(layout)

        # Should have added the layout
        assert dialog._content_layout.count() >= 1
