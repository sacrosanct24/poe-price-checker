"""Tests for gui_qt/feedback/feedback_collector.py - Feedback collection."""

import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from tempfile import TemporaryDirectory

from gui_qt.feedback.feedback_collector import (
    FeedbackType,
    FEEDBACK_TYPE_LABELS,
    FEEDBACK_TYPE_HINTS,
    SystemInfo,
    FeedbackEntry,
    FeedbackCollector,
    FeedbackDialog,
)


# =============================================================================
# FeedbackType Tests
# =============================================================================


class TestFeedbackType:
    """Tests for FeedbackType enum."""

    def test_has_bug_type(self):
        """Should have bug type."""
        assert FeedbackType.BUG.value == "bug"

    def test_has_feature_type(self):
        """Should have feature type."""
        assert FeedbackType.FEATURE.value == "feature"

    def test_has_improvement_type(self):
        """Should have improvement type."""
        assert FeedbackType.IMPROVEMENT.value == "improvement"

    def test_has_other_type(self):
        """Should have other type."""
        assert FeedbackType.OTHER.value == "other"

    def test_all_types_have_labels(self):
        """All types should have labels."""
        for fb_type in FeedbackType:
            assert fb_type in FEEDBACK_TYPE_LABELS

    def test_all_types_have_hints(self):
        """All types should have hints."""
        for fb_type in FeedbackType:
            assert fb_type in FEEDBACK_TYPE_HINTS


# =============================================================================
# SystemInfo Tests
# =============================================================================


class TestSystemInfo:
    """Tests for SystemInfo dataclass."""

    def test_collect_returns_instance(self):
        """Should return SystemInfo instance."""
        info = SystemInfo.collect()
        assert isinstance(info, SystemInfo)

    def test_collect_with_app_version(self):
        """Should include app version."""
        info = SystemInfo.collect(app_version="1.0.0")
        assert info.app_version == "1.0.0"

    def test_has_os_info(self):
        """Should have OS information."""
        info = SystemInfo.collect()
        assert info.os is not None
        assert len(info.os) > 0

    def test_has_python_version(self):
        """Should have Python version."""
        info = SystemInfo.collect()
        assert info.python_version is not None
        assert "." in info.python_version


# =============================================================================
# FeedbackEntry Tests
# =============================================================================


class TestFeedbackEntry:
    """Tests for FeedbackEntry dataclass."""

    def test_to_dict_basic(self):
        """Should convert to dictionary."""
        entry = FeedbackEntry(
            id="test_123",
            type=FeedbackType.BUG,
            message="Test message",
            timestamp="2024-01-01T00:00:00",
        )

        result = entry.to_dict()

        assert result["id"] == "test_123"
        assert result["type"] == "bug"
        assert result["message"] == "Test message"

    def test_to_dict_with_context(self):
        """Should include context if present."""
        entry = FeedbackEntry(
            id="test_123",
            type=FeedbackType.BUG,
            message="Test",
            timestamp="2024-01-01T00:00:00",
            context="Price checking",
        )

        result = entry.to_dict()

        assert result["context"] == "Price checking"

    def test_to_dict_with_system_info(self):
        """Should include system info if present."""
        info = SystemInfo(
            os="Windows",
            os_version="10",
            python_version="3.13",
            app_version="1.0",
        )
        entry = FeedbackEntry(
            id="test_123",
            type=FeedbackType.BUG,
            message="Test",
            timestamp="2024-01-01T00:00:00",
            system_info=info,
        )

        result = entry.to_dict()

        assert "system_info" in result
        assert result["system_info"]["os"] == "Windows"

    def test_to_dict_without_optional_fields(self):
        """Should not include optional fields if None."""
        entry = FeedbackEntry(
            id="test_123",
            type=FeedbackType.BUG,
            message="Test",
            timestamp="2024-01-01T00:00:00",
            context=None,
            system_info=None,
        )

        result = entry.to_dict()

        assert "context" not in result
        assert "system_info" not in result


# =============================================================================
# FeedbackCollector Tests
# =============================================================================


class TestFeedbackCollectorInit:
    """Tests for FeedbackCollector initialization."""

    def test_init_creates_storage_dir(self):
        """Should create storage directory."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "feedback_test"
            FeedbackCollector(storage_dir=storage_path)

            assert storage_path.exists()

    def test_init_default_storage(self):
        """Should use default storage when None."""
        with patch('core.config.get_config_dir') as mock_get:
            with TemporaryDirectory() as tmpdir:
                mock_get.return_value = Path(tmpdir)
                collector = FeedbackCollector(storage_dir=None)

                assert collector._storage_dir.exists()


class TestFeedbackCollectorCollect:
    """Tests for feedback collection."""

    def test_collect_returns_entry(self):
        """Should return FeedbackEntry."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            entry = collector.collect(
                type=FeedbackType.BUG,
                message="Test bug report",
            )

            assert isinstance(entry, FeedbackEntry)
            assert entry.type == FeedbackType.BUG
            assert entry.message == "Test bug report"

    def test_collect_generates_id(self):
        """Should generate unique ID."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            entry = collector.collect(
                type=FeedbackType.FEATURE,
                message="Test",
            )

            assert entry.id is not None
            assert "feature" in entry.id

    def test_collect_with_context(self):
        """Should include context."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            entry = collector.collect(
                type=FeedbackType.BUG,
                message="Test",
                context="Checking prices",
            )

            assert entry.context == "Checking prices"

    def test_collect_with_contact(self):
        """Should include contact."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            entry = collector.collect(
                type=FeedbackType.BUG,
                message="Test",
                contact="test@example.com",
            )

            assert entry.contact == "test@example.com"

    def test_collect_with_system_info(self):
        """Should include system info when requested."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            entry = collector.collect(
                type=FeedbackType.BUG,
                message="Test",
                include_system_info=True,
            )

            assert entry.system_info is not None

    def test_collect_without_system_info(self):
        """Should not include system info when not requested."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            entry = collector.collect(
                type=FeedbackType.BUG,
                message="Test",
                include_system_info=False,
            )

            assert entry.system_info is None

    def test_collect_stores_feedback(self):
        """Should store feedback to file."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            collector.collect(
                type=FeedbackType.BUG,
                message="Test bug",
            )

            # Check file exists
            assert collector._feedback_file.exists()

            # Check content
            with open(collector._feedback_file) as f:
                data = json.load(f)
            assert len(data) == 1
            assert data[0]["message"] == "Test bug"


class TestFeedbackCollectorGetStoredFeedback:
    """Tests for retrieving stored feedback."""

    def test_get_stored_feedback_empty(self):
        """Should return empty list when no feedback."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            result = collector.get_stored_feedback()

            assert result == []

    def test_get_stored_feedback_returns_list(self):
        """Should return list of feedback."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            collector.collect(type=FeedbackType.BUG, message="Bug 1")
            collector.collect(type=FeedbackType.FEATURE, message="Feature 1")

            result = collector.get_stored_feedback()

            assert len(result) == 2

    def test_get_stored_feedback_handles_error(self):
        """Should handle file errors gracefully."""
        with TemporaryDirectory() as tmpdir:
            collector = FeedbackCollector(storage_dir=Path(tmpdir))

            # Create invalid JSON file
            with open(collector._feedback_file, "w") as f:
                f.write("invalid json")

            result = collector.get_stored_feedback()

            assert result == []


# =============================================================================
# FeedbackDialog Tests
# =============================================================================


class TestFeedbackDialogInit:
    """Tests for FeedbackDialog initialization."""

    def test_init_sets_title(self, qtbot):
        """Should set window title."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        assert "Feedback" in dialog.windowTitle()

    def test_init_sets_minimum_size(self, qtbot):
        """Should set minimum size."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 500
        assert dialog.minimumHeight() >= 400

    def test_init_creates_type_combo(self, qtbot):
        """Should create type combo box."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        assert dialog._type_combo is not None
        assert dialog._type_combo.count() == len(FeedbackType)

    def test_init_creates_message_edit(self, qtbot):
        """Should create message text edit."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        assert dialog._message_edit is not None

    def test_init_with_initial_type(self, qtbot):
        """Should set initial type."""
        dialog = FeedbackDialog(initial_type=FeedbackType.FEATURE)
        qtbot.addWidget(dialog)

        current_type = dialog._type_combo.currentData()
        assert current_type == FeedbackType.FEATURE

    def test_init_has_signal(self, qtbot):
        """Should have feedback_submitted signal."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, 'feedback_submitted')


class TestFeedbackDialogTypeChange:
    """Tests for type change handling."""

    def test_on_type_changed_updates_hint(self, qtbot):
        """Should update hint when type changes."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        # Change to FEATURE
        dialog._type_combo.setCurrentIndex(
            list(FeedbackType).index(FeedbackType.FEATURE)
        )

        assert FEEDBACK_TYPE_HINTS[FeedbackType.FEATURE] in dialog._hint_label.text()


class TestFeedbackDialogSubmit:
    """Tests for submit functionality."""

    def test_submit_empty_message_shows_warning(self, qtbot):
        """Should show warning for empty message."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        dialog._message_edit.clear()

        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog._submit()
            mock_warning.assert_called_once()

    def test_submit_with_message_collects_feedback(self, qtbot):
        """Should collect feedback with valid message."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        dialog._message_edit.setText("Test feedback message")

        # Return a real FeedbackEntry to avoid signal type error
        mock_entry = FeedbackEntry(
            id="test_123",
            type=FeedbackType.BUG,
            message="Test feedback message",
            timestamp="2024-01-01T00:00:00",
        )

        with patch.object(dialog._collector, 'collect', return_value=mock_entry) as mock_collect:
            with patch('PyQt6.QtWidgets.QMessageBox.information'):
                dialog._submit()

            mock_collect.assert_called_once()

    def test_submit_emits_signal(self, qtbot):
        """Should emit feedback_submitted signal."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        dialog._message_edit.setText("Test feedback")

        received = []
        dialog.feedback_submitted.connect(lambda e: received.append(e))

        with patch('PyQt6.QtWidgets.QMessageBox.information'):
            dialog._submit()

        assert len(received) == 1

    def test_submit_includes_context(self, qtbot):
        """Should include context in feedback."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        dialog._message_edit.setText("Test feedback")
        dialog._context_edit.setText("Checking item prices")

        mock_entry = FeedbackEntry(
            id="test_123",
            type=FeedbackType.BUG,
            message="Test feedback",
            timestamp="2024-01-01T00:00:00",
        )

        with patch.object(dialog._collector, 'collect', return_value=mock_entry) as mock_collect:
            with patch('PyQt6.QtWidgets.QMessageBox.information'):
                dialog._submit()

            call_kwargs = mock_collect.call_args[1]
            assert call_kwargs["context"] == "Checking item prices"

    def test_submit_includes_contact(self, qtbot):
        """Should include contact in feedback."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        dialog._message_edit.setText("Test feedback")
        dialog._contact_edit.setText("user@example.com")

        mock_entry = FeedbackEntry(
            id="test_123",
            type=FeedbackType.BUG,
            message="Test feedback",
            timestamp="2024-01-01T00:00:00",
        )

        with patch.object(dialog._collector, 'collect', return_value=mock_entry) as mock_collect:
            with patch('PyQt6.QtWidgets.QMessageBox.information'):
                dialog._submit()

            call_kwargs = mock_collect.call_args[1]
            assert call_kwargs["contact"] == "user@example.com"


class TestFeedbackDialogOptions:
    """Tests for dialog options."""

    def test_include_system_checked_by_default(self, qtbot):
        """Should have include system info checked by default."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        assert dialog._include_system_cb.isChecked()

    def test_include_logs_unchecked_by_default(self, qtbot):
        """Should have include logs unchecked by default."""
        dialog = FeedbackDialog()
        qtbot.addWidget(dialog)

        assert not dialog._include_logs_cb.isChecked()
