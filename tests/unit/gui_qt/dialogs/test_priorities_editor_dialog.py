"""Tests for gui_qt/dialogs/priorities_editor_dialog.py - Build priorities editor."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from core.build_priorities import BuildPriorities, StatPriority, PriorityTier

from gui_qt.dialogs.priorities_editor_dialog import PrioritiesEditorDialog


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_character_manager():
    """Create a mock character manager."""
    manager = MagicMock()
    profile = MagicMock()
    profile.priorities = None
    profile.build = MagicMock()
    profile.build.stats = {"life": 5000, "es": 0}
    manager.get_profile.return_value = profile
    return manager


@pytest.fixture
def mock_priorities():
    """Create sample priorities."""
    priorities = BuildPriorities()
    priorities.add_priority("life", PriorityTier.CRITICAL, min_value=100)
    priorities.add_priority("es", PriorityTier.IMPORTANT)
    priorities.add_priority("dexterity", PriorityTier.NICE_TO_HAVE)
    return priorities


# =============================================================================
# PrioritiesEditorDialog Init Tests
# =============================================================================


class TestPrioritiesEditorDialogInit:
    """Tests for dialog initialization."""

    def test_init_sets_title(self, qtbot):
        """Should set window title."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        assert "Priorities" in dialog.windowTitle()

    def test_init_sets_minimum_size(self, qtbot):
        """Should set minimum size."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 500
        assert dialog.minimumHeight() >= 650

    def test_init_creates_widgets(self, qtbot):
        """Should create required widgets."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        assert dialog.stat_combo is not None
        assert dialog.tier_combo is not None
        assert dialog.min_value_input is not None
        assert dialog.critical_list is not None
        assert dialog.important_list is not None
        assert dialog.nice_list is not None

    def test_init_stores_parameters(self, qtbot, mock_character_manager):
        """Should store constructor parameters."""
        callback = MagicMock()
        dialog = PrioritiesEditorDialog(
            character_manager=mock_character_manager,
            profile_name="TestProfile",
            on_save=callback,
        )
        qtbot.addWidget(dialog)

        assert dialog.character_manager is mock_character_manager
        assert dialog.profile_name == "TestProfile"
        assert dialog.on_save is callback

    def test_init_loads_profile(self, qtbot, mock_character_manager):
        """Should load profile on init."""
        dialog = PrioritiesEditorDialog(
            character_manager=mock_character_manager,
            profile_name="TestProfile",
        )
        qtbot.addWidget(dialog)

        mock_character_manager.get_profile.assert_called_with("TestProfile")


class TestPrioritiesEditorDialogStatCombo:
    """Tests for stat combo box."""

    def test_stat_combo_populated(self, qtbot):
        """Should populate stat combo with available stats."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        assert dialog.stat_combo.count() > 0

    def test_tier_combo_has_tiers(self, qtbot):
        """Should have all priority tiers."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        assert dialog.tier_combo.count() == 3  # Critical, Important, Nice to Have


# =============================================================================
# Build Type Tests
# =============================================================================


class TestPrioritiesEditorDialogBuildType:
    """Tests for build type functionality."""

    def test_init_has_build_type_buttons(self, qtbot):
        """Should have build type buttons."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        assert dialog.life_build_btn is not None
        assert dialog.es_build_btn is not None
        assert dialog.hybrid_btn is not None

    def test_set_build_type_life(self, qtbot):
        """Should set life build type."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._set_build_type("life")

        assert dialog._priorities.is_life_build is True
        assert dialog._priorities.is_es_build is False
        assert dialog._priorities.is_hybrid is False

    def test_set_build_type_es(self, qtbot):
        """Should set ES build type."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._set_build_type("es")

        assert dialog._priorities.is_life_build is False
        assert dialog._priorities.is_es_build is True
        assert dialog._priorities.is_hybrid is False

    def test_set_build_type_hybrid(self, qtbot):
        """Should set hybrid build type."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._set_build_type("hybrid")

        assert dialog._priorities.is_life_build is False
        assert dialog._priorities.is_es_build is False
        assert dialog._priorities.is_hybrid is True

    def test_update_build_type_buttons(self, qtbot, mock_priorities):
        """Should update button states based on priorities."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = mock_priorities
        mock_priorities.is_life_build = True
        mock_priorities.is_es_build = False
        mock_priorities.is_hybrid = False

        dialog._update_build_type_buttons()

        assert dialog.life_build_btn.isChecked()
        assert not dialog.es_build_btn.isChecked()
        assert not dialog.hybrid_btn.isChecked()


# =============================================================================
# Add Stat Tests
# =============================================================================


class TestPrioritiesEditorDialogAddStat:
    """Tests for adding stats."""

    def test_add_stat_creates_priorities_if_none(self, qtbot):
        """Should create priorities object if None."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = None
        dialog._add_stat()

        assert dialog._priorities is not None

    def test_add_stat_adds_to_correct_tier(self, qtbot):
        """Should add stat to selected tier."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        # Select a stat and tier
        dialog.stat_combo.setCurrentIndex(0)
        dialog.tier_combo.setCurrentIndex(0)  # Critical

        dialog._add_stat()

        assert len(dialog._priorities.critical) == 1

    def test_add_stat_with_min_value(self, qtbot):
        """Should add stat with minimum value."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog.stat_combo.setCurrentIndex(0)
        dialog.tier_combo.setCurrentIndex(0)
        dialog.min_value_input.setText("100")

        dialog._add_stat()

        assert dialog._priorities.critical[0].min_value == 100

    def test_add_stat_clears_min_value_input(self, qtbot):
        """Should clear min value input after adding."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog.min_value_input.setText("100")
        dialog._add_stat()

        assert dialog.min_value_input.text() == ""


# =============================================================================
# Remove Stat Tests
# =============================================================================


class TestPrioritiesEditorDialogRemoveStat:
    """Tests for removing stats."""

    def test_remove_stat_removes_from_priorities(self, qtbot):
        """Should remove stat from priorities."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        # Add a stat first
        dialog._priorities = BuildPriorities()
        dialog._priorities.add_priority("life", PriorityTier.CRITICAL)
        dialog._refresh_lists()

        # Create item with stat type
        item = QListWidgetItem("Life")
        item.setData(Qt.ItemDataRole.UserRole, "life")

        dialog._remove_stat(item)

        assert len(dialog._priorities.critical) == 0

    def test_remove_stat_does_nothing_if_no_priorities(self, qtbot):
        """Should handle None priorities gracefully."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = None
        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, "life")

        # Should not raise
        dialog._remove_stat(item)


# =============================================================================
# Move Stat Tests
# =============================================================================


class TestPrioritiesEditorDialogMoveStat:
    """Tests for moving stats between tiers."""

    def test_move_stat_to_different_tier(self, qtbot):
        """Should move stat to different tier."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = BuildPriorities()
        dialog._priorities.add_priority("life", PriorityTier.CRITICAL, min_value=100)

        item = QListWidgetItem("Life")
        item.setData(Qt.ItemDataRole.UserRole, "life")

        dialog._move_stat(item, PriorityTier.IMPORTANT)

        assert len(dialog._priorities.critical) == 0
        assert len(dialog._priorities.important) == 1
        # Should preserve min value
        assert dialog._priorities.important[0].min_value == 100

    def test_move_stat_does_nothing_if_no_priorities(self, qtbot):
        """Should handle None priorities gracefully."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = None
        item = QListWidgetItem("Test")
        item.setData(Qt.ItemDataRole.UserRole, "life")

        # Should not raise
        dialog._move_stat(item, PriorityTier.IMPORTANT)


# =============================================================================
# Refresh Lists Tests
# =============================================================================


class TestPrioritiesEditorDialogRefreshLists:
    """Tests for refreshing list widgets."""

    def test_refresh_lists_clears_existing(self, qtbot):
        """Should clear existing items."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog.critical_list.addItem("Old item")
        dialog._priorities = BuildPriorities()

        dialog._refresh_lists()

        assert dialog.critical_list.count() == 0

    def test_refresh_lists_populates_from_priorities(self, qtbot, mock_priorities):
        """Should populate lists from priorities."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = mock_priorities
        dialog._refresh_lists()

        assert dialog.critical_list.count() == 1
        assert dialog.important_list.count() == 1
        assert dialog.nice_list.count() == 1

    def test_refresh_lists_handles_none_priorities(self, qtbot):
        """Should handle None priorities."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = None

        # Should not raise
        dialog._refresh_lists()

        assert dialog.critical_list.count() == 0


# =============================================================================
# Add Item to List Tests
# =============================================================================


class TestPrioritiesEditorDialogAddItemToList:
    """Tests for adding items to list widgets."""

    def test_add_item_to_list_basic(self, qtbot):
        """Should add item with stat name."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        priority = StatPriority(stat_type="life", tier=PriorityTier.CRITICAL)
        dialog._add_item_to_list(dialog.critical_list, priority)

        assert dialog.critical_list.count() == 1

    def test_add_item_to_list_with_min_value(self, qtbot):
        """Should include min value in text."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        priority = StatPriority(
            stat_type="life",
            tier=PriorityTier.CRITICAL,
            min_value=100,
        )
        dialog._add_item_to_list(dialog.critical_list, priority)

        item = dialog.critical_list.item(0)
        assert "100" in item.text()

    def test_add_item_to_list_stores_stat_type(self, qtbot):
        """Should store stat type in item data."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        priority = StatPriority(stat_type="life", tier=PriorityTier.CRITICAL)
        dialog._add_item_to_list(dialog.critical_list, priority)

        item = dialog.critical_list.item(0)
        assert item.data(Qt.ItemDataRole.UserRole) == "life"


# =============================================================================
# Auto Suggest Tests
# =============================================================================


class TestPrioritiesEditorDialogAutoSuggest:
    """Tests for auto-suggest functionality."""

    def test_auto_suggest_does_nothing_without_manager(self, qtbot):
        """Should return if no character manager."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog.character_manager = None

        # Should not raise
        dialog._auto_suggest()

    def test_auto_suggest_shows_warning_if_no_build(self, qtbot, mock_character_manager):
        """Should show warning if no build data."""
        mock_character_manager.get_profile.return_value.build = None

        dialog = PrioritiesEditorDialog(
            character_manager=mock_character_manager,
            profile_name="TestProfile",
        )
        qtbot.addWidget(dialog)

        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            dialog._auto_suggest()
            mock_warning.assert_called_once()


# =============================================================================
# Save Tests
# =============================================================================


class TestPrioritiesEditorDialogSave:
    """Tests for save functionality."""

    def test_save_creates_priorities_if_none(self, qtbot):
        """Should create priorities if None."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = None

        with patch.object(dialog, 'accept'):
            dialog._save()

        assert dialog._priorities is not None

    def test_save_calls_callback(self, qtbot):
        """Should call on_save callback."""
        callback = MagicMock()
        dialog = PrioritiesEditorDialog(on_save=callback)
        qtbot.addWidget(dialog)

        dialog._priorities = BuildPriorities()

        with patch.object(dialog, 'accept'):
            dialog._save()

        callback.assert_called_once_with(dialog._priorities)

    def test_save_updates_character_manager(self, qtbot, mock_character_manager):
        """Should update character manager."""
        dialog = PrioritiesEditorDialog(
            character_manager=mock_character_manager,
            profile_name="TestProfile",
        )
        qtbot.addWidget(dialog)

        dialog._priorities = BuildPriorities()

        with patch.object(dialog, 'accept'):
            dialog._save()

        mock_character_manager.set_priorities.assert_called_once()


# =============================================================================
# Get Priorities Tests
# =============================================================================


class TestPrioritiesEditorDialogGetPriorities:
    """Tests for get_priorities method."""

    def test_get_priorities_returns_current(self, qtbot, mock_priorities):
        """Should return current priorities."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = mock_priorities

        result = dialog.get_priorities()

        assert result is mock_priorities

    def test_get_priorities_returns_none_if_not_set(self, qtbot):
        """Should return None if not set."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        dialog._priorities = None

        result = dialog.get_priorities()

        assert result is None


# =============================================================================
# Load Profile Tests
# =============================================================================


class TestPrioritiesEditorDialogLoadProfile:
    """Tests for profile loading."""

    def test_load_profile_does_nothing_without_manager(self, qtbot):
        """Should return early without manager."""
        dialog = PrioritiesEditorDialog()
        qtbot.addWidget(dialog)

        # Should not raise
        dialog._load_profile()

    def test_load_profile_loads_existing_priorities(self, qtbot, mock_character_manager, mock_priorities):
        """Should load existing priorities from profile."""
        profile = mock_character_manager.get_profile.return_value
        profile.priorities = mock_priorities

        dialog = PrioritiesEditorDialog(
            character_manager=mock_character_manager,
            profile_name="TestProfile",
        )
        qtbot.addWidget(dialog)

        assert dialog._priorities is mock_priorities

    def test_load_profile_creates_new_if_none(self, qtbot, mock_character_manager):
        """Should create new priorities if profile has none."""
        profile = mock_character_manager.get_profile.return_value
        profile.priorities = None

        dialog = PrioritiesEditorDialog(
            character_manager=mock_character_manager,
            profile_name="TestProfile",
        )
        qtbot.addWidget(dialog)

        assert dialog._priorities is not None
        assert isinstance(dialog._priorities, BuildPriorities)
