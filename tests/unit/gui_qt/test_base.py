"""Tests for gui_qt.base module - base classes for PyQt6 components."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QMessageBox

from gui_qt.base import BaseWindow, BaseDialog


@pytest.fixture
def mock_ctx():
    """Create a mock IAppContext."""
    ctx = MagicMock()
    ctx.config = MagicMock()
    ctx.parser = MagicMock()
    ctx.price_service = MagicMock()
    return ctx


class TestBaseWindowInit:
    """Tests for BaseWindow initialization."""

    def test_init_with_context(self, qtbot, mock_ctx):
        """BaseWindow initializes with context."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.ctx is mock_ctx

    def test_init_with_parent(self, qtbot, mock_ctx):
        """BaseWindow can have a parent."""
        parent = QWidget()
        qtbot.addWidget(parent)

        window = BaseWindow(mock_ctx, parent=parent)
        qtbot.addWidget(window)

        assert window.parent() is parent

    def test_init_without_parent(self, qtbot, mock_ctx):
        """BaseWindow works without parent."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)

        assert window.parent() is None


class TestBaseWindowCenterOnScreen:
    """Tests for BaseWindow.center_on_screen."""

    def test_center_on_screen(self, qtbot, mock_ctx):
        """Window centers on screen."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)
        window.resize(400, 300)
        window.show()

        window.center_on_screen()

        # Verify window is visible and has been moved
        assert window.isVisible()
        # The exact position depends on screen size, just verify it moved
        screen = window.screen()
        if screen:
            screen_center = screen.availableGeometry().center()
            window_center = window.frameGeometry().center()
            # Window center should be reasonably close to screen center
            assert abs(window_center.x() - screen_center.x()) < 10
            assert abs(window_center.y() - screen_center.y()) < 10

    def test_center_on_screen_no_screen(self, qtbot, mock_ctx):
        """center_on_screen handles no screen gracefully."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)

        # Mock screen() to return None
        with patch.object(window, 'screen', return_value=None):
            # Should not raise
            window.center_on_screen()


class TestBaseWindowCenterOnParent:
    """Tests for BaseWindow.center_on_parent."""

    def test_center_on_parent_with_parent(self, qtbot, mock_ctx):
        """Window centers on parent widget."""
        parent = QWidget()
        parent.setGeometry(100, 100, 800, 600)
        qtbot.addWidget(parent)
        parent.show()

        window = BaseWindow(mock_ctx, parent=parent)
        window.resize(200, 150)
        qtbot.addWidget(window)
        window.show()

        window.center_on_parent()

        # Window should be centered on parent
        parent_geo = parent.geometry()
        window_geo = window.geometry()

        expected_x = parent_geo.x() + (parent_geo.width() - window_geo.width()) // 2
        expected_y = parent_geo.y() + (parent_geo.height() - window_geo.height()) // 2

        assert window.x() == expected_x
        assert window.y() == expected_y

    def test_center_on_parent_without_parent(self, qtbot, mock_ctx):
        """Window falls back to screen centering without parent."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)
        window.resize(200, 150)
        window.show()

        # Should not raise and should call center_on_screen
        with patch.object(window, 'center_on_screen') as mock_center:
            window.center_on_parent()
            mock_center.assert_called_once()

    def test_center_on_parent_non_widget_parent(self, qtbot, mock_ctx):
        """Window handles non-QWidget parent gracefully."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)

        # Mock parent() to return a non-widget
        with patch.object(window, 'parent', return_value=MagicMock()):
            with patch.object(window, 'center_on_screen') as mock_center:
                window.center_on_parent()
                mock_center.assert_called_once()


class TestBaseDialogInit:
    """Tests for BaseDialog initialization."""

    def test_init_with_title(self, qtbot):
        """BaseDialog sets title."""
        dialog = BaseDialog(title="Test Dialog")
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Test Dialog"

    def test_init_without_title(self, qtbot):
        """BaseDialog works without title."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == ""

    def test_init_with_parent(self, qtbot):
        """BaseDialog can have a parent."""
        parent = QWidget()
        qtbot.addWidget(parent)

        dialog = BaseDialog(parent=parent, title="Child Dialog")
        qtbot.addWidget(dialog)

        assert dialog.parent() is parent

    def test_init_removes_help_button(self, qtbot):
        """BaseDialog removes context help button."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        # Check that help button hint is removed
        flags = dialog.windowFlags()
        assert not (flags & Qt.WindowType.WindowContextHelpButtonHint)


class TestBaseDialogCenterOnParent:
    """Tests for BaseDialog.center_on_parent."""

    def test_center_on_parent_with_parent(self, qtbot):
        """Dialog centers on parent widget."""
        parent = QWidget()
        parent.setGeometry(200, 200, 600, 400)
        qtbot.addWidget(parent)
        parent.show()

        dialog = BaseDialog(parent=parent)
        dialog.resize(200, 100)
        qtbot.addWidget(dialog)
        dialog.show()

        dialog.center_on_parent()

        # Dialog should be centered on parent
        parent_geo = parent.geometry()
        dialog_geo = dialog.geometry()

        expected_x = parent_geo.x() + (parent_geo.width() - dialog_geo.width()) // 2
        expected_y = parent_geo.y() + (parent_geo.height() - dialog_geo.height()) // 2

        assert dialog.x() == expected_x
        assert dialog.y() == expected_y

    def test_center_on_parent_without_parent(self, qtbot):
        """center_on_parent does nothing without parent."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)
        dialog.resize(200, 100)
        dialog.move(0, 0)
        dialog.show()

        original_pos = dialog.pos()
        dialog.center_on_parent()

        # Position should remain unchanged (no parent to center on)
        assert dialog.pos() == original_pos


class TestBaseDialogShowError:
    """Tests for BaseDialog.show_error."""

    def test_show_error_creates_message_box(self, qtbot):
        """show_error displays critical message box."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, 'critical') as mock_critical:
            dialog.show_error("Error Title", "Error message")

            mock_critical.assert_called_once_with(
                dialog, "Error Title", "Error message"
            )


class TestBaseDialogShowInfo:
    """Tests for BaseDialog.show_info."""

    def test_show_info_creates_message_box(self, qtbot):
        """show_info displays information message box."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, 'information') as mock_info:
            dialog.show_info("Info Title", "Info message")

            mock_info.assert_called_once_with(
                dialog, "Info Title", "Info message"
            )


class TestBaseDialogAskYesNo:
    """Tests for BaseDialog.ask_yes_no."""

    def test_ask_yes_no_returns_true_on_yes(self, qtbot):
        """ask_yes_no returns True when user clicks Yes."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        with patch.object(
            QMessageBox, 'question',
            return_value=QMessageBox.StandardButton.Yes
        ):
            result = dialog.ask_yes_no("Confirm", "Do you want to proceed?")

            assert result is True

    def test_ask_yes_no_returns_false_on_no(self, qtbot):
        """ask_yes_no returns False when user clicks No."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        with patch.object(
            QMessageBox, 'question',
            return_value=QMessageBox.StandardButton.No
        ):
            result = dialog.ask_yes_no("Confirm", "Do you want to proceed?")

            assert result is False

    def test_ask_yes_no_question_parameters(self, qtbot):
        """ask_yes_no passes correct parameters to QMessageBox."""
        dialog = BaseDialog()
        qtbot.addWidget(dialog)

        with patch.object(
            QMessageBox, 'question',
            return_value=QMessageBox.StandardButton.No
        ) as mock_question:
            dialog.ask_yes_no("Title", "Message")

            mock_question.assert_called_once_with(
                dialog,
                "Title",
                "Message",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )


class TestBaseDialogEdgeCases:
    """Tests for edge cases in BaseDialog."""

    def test_empty_title(self, qtbot):
        """Dialog handles empty title."""
        dialog = BaseDialog(title="")
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == ""

    def test_long_title(self, qtbot):
        """Dialog handles long title."""
        long_title = "A" * 500
        dialog = BaseDialog(title=long_title)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == long_title

    def test_special_characters_in_title(self, qtbot):
        """Dialog handles special characters in title."""
        special_title = "Test <Dialog> & \"More\" 'Stuff'"
        dialog = BaseDialog(title=special_title)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == special_title


class TestBaseWindowEdgeCases:
    """Tests for edge cases in BaseWindow."""

    def test_resize_before_center(self, qtbot, mock_ctx):
        """Window can be resized before centering."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)

        window.resize(800, 600)
        window.center_on_screen()

        assert window.width() == 800
        assert window.height() == 600

    def test_multiple_center_calls(self, qtbot, mock_ctx):
        """Multiple center calls work correctly."""
        window = BaseWindow(mock_ctx)
        qtbot.addWidget(window)
        window.resize(400, 300)
        window.show()

        # Call multiple times - should not raise
        window.center_on_screen()
        window.center_on_screen()
        window.center_on_parent()
        window.center_on_parent()

        assert window.isVisible()
