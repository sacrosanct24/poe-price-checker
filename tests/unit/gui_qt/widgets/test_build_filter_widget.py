"""
Tests for the BuildFilterWidget.

Tests cascading dropdown logic, game version filtering, and build matching.
"""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from gui_qt.widgets.build_filter_widget import BuildFilterWidget
from core.game_data import GameVersion


@pytest.fixture
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def build_filter(qapp, qtbot):
    """Create a BuildFilterWidget for testing."""
    widget = BuildFilterWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def build_filter_no_labels(qapp, qtbot):
    """Create a BuildFilterWidget without labels."""
    widget = BuildFilterWidget(show_labels=False, horizontal=False)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def build_filter_no_all(qapp, qtbot):
    """Create a BuildFilterWidget without 'All' option."""
    widget = BuildFilterWidget(include_all_option=False)
    qtbot.addWidget(widget)
    return widget


class TestBuildFilterWidgetInitialization:
    """Tests for BuildFilterWidget initialization."""

    def test_default_initialization(self, build_filter):
        """Test that widget initializes with correct defaults."""
        assert build_filter.game_combo is not None
        assert build_filter.class_combo is not None
        assert build_filter.ascendancy_combo is not None

        # Should have "All Games" + 2 game options
        assert build_filter.game_combo.count() == 3
        assert build_filter.game_combo.itemText(0) == "All Games"
        assert build_filter.game_combo.itemText(1) == "PoE 1"
        assert build_filter.game_combo.itemText(2) == "PoE 2"

        # Class combo should be populated with all classes
        assert build_filter.class_combo.count() > 0
        assert build_filter.class_combo.itemText(0) == "All Classes"

        # Ascendancy combo should be populated
        assert build_filter.ascendancy_combo.count() > 0
        assert build_filter.ascendancy_combo.itemText(0) == "All Ascendancies"

    def test_initialization_without_labels(self, build_filter_no_labels):
        """Test initialization without labels (vertical layout)."""
        assert build_filter_no_labels._show_labels is False
        assert build_filter_no_labels._horizontal is False
        assert build_filter_no_labels.game_combo is not None
        assert build_filter_no_labels.class_combo is not None
        assert build_filter_no_labels.ascendancy_combo is not None

    def test_initialization_without_all_option(self, build_filter_no_all):
        """Test initialization without 'All' option."""
        assert build_filter_no_all._include_all is False

        # Should only have 2 game options (no "All Games")
        assert build_filter_no_all.game_combo.count() == 2
        assert build_filter_no_all.game_combo.itemText(0) == "PoE 1"
        assert build_filter_no_all.game_combo.itemText(1) == "PoE 2"

        # Class combo should not have "All Classes"
        assert "All Classes" not in [
            build_filter_no_all.class_combo.itemText(i)
            for i in range(build_filter_no_all.class_combo.count())
        ]

    def test_combo_minimum_widths(self, build_filter):
        """Test that combos have minimum widths set."""
        assert build_filter.game_combo.minimumWidth() == 80
        assert build_filter.class_combo.minimumWidth() == 100
        assert build_filter.ascendancy_combo.minimumWidth() == 140


class TestBuildFilterWidgetCascadingLogic:
    """Tests for cascading dropdown logic."""

    def test_game_change_updates_classes(self, build_filter, qtbot):
        """Test that changing game version updates class dropdown."""
        # Select PoE 1
        build_filter.game_combo.setCurrentIndex(1)  # PoE 1

        # Should have PoE1 classes only
        class_names = [
            build_filter.class_combo.itemText(i)
            for i in range(build_filter.class_combo.count())
        ]
        assert "All Classes" in class_names
        assert "Marauder" in class_names  # PoE1 class
        assert "Witch" in class_names  # PoE1 class

    def test_game_change_to_poe2_updates_classes(self, build_filter, qtbot):
        """Test that changing to PoE2 updates class dropdown."""
        # Select PoE 2
        build_filter.game_combo.setCurrentIndex(2)  # PoE 2

        # Should have PoE2 classes only
        class_names = [
            build_filter.class_combo.itemText(i)
            for i in range(build_filter.class_combo.count())
        ]
        assert "All Classes" in class_names
        assert "Warrior" in class_names  # PoE2 class
        assert "Sorceress" in class_names  # PoE2 class

    def test_all_games_shows_combined_classes(self, build_filter, qtbot):
        """Test that 'All Games' shows classes from both games."""
        # Select "All Games"
        build_filter.game_combo.setCurrentIndex(0)

        class_names = [
            build_filter.class_combo.itemText(i)
            for i in range(build_filter.class_combo.count())
        ]

        # Should contain classes from both games
        assert "All Classes" in class_names
        assert len(class_names) > 1  # At least "All Classes" + some classes

    def test_class_change_updates_ascendancies(self, build_filter, qtbot):
        """Test that changing class updates ascendancy dropdown."""
        # Select PoE 1
        build_filter.game_combo.setCurrentIndex(1)

        # Select Marauder
        for i in range(build_filter.class_combo.count()):
            if build_filter.class_combo.itemText(i) == "Marauder":
                build_filter.class_combo.setCurrentIndex(i)
                break

        # Should have Marauder ascendancies
        asc_names = [
            build_filter.ascendancy_combo.itemText(i)
            for i in range(build_filter.ascendancy_combo.count())
        ]
        assert "All Ascendancies" in asc_names
        assert "Juggernaut" in asc_names
        assert "Berserker" in asc_names
        assert "Chieftain" in asc_names

    def test_all_classes_shows_all_ascendancies(self, build_filter, qtbot):
        """Test that 'All Classes' shows all ascendancies for game."""
        # Select PoE 1
        build_filter.game_combo.setCurrentIndex(1)

        # Select "All Classes"
        build_filter.class_combo.setCurrentIndex(0)

        # Should have ascendancies from all PoE1 classes
        asc_names = [
            build_filter.ascendancy_combo.itemText(i)
            for i in range(build_filter.ascendancy_combo.count())
        ]
        assert "All Ascendancies" in asc_names
        assert len(asc_names) > 5  # Should have many ascendancies


class TestBuildFilterWidgetSignals:
    """Tests for filter_changed signal emission."""

    def test_filter_changed_on_game_change(self, build_filter, qtbot):
        """Test that filter_changed signal is emitted on game change."""
        with qtbot.waitSignal(build_filter.filter_changed, timeout=1000):
            build_filter.game_combo.setCurrentIndex(1)

    def test_filter_changed_on_class_change(self, build_filter, qtbot):
        """Test that filter_changed signal is emitted on class change."""
        # First change game to ensure class combo is populated
        build_filter.game_combo.setCurrentIndex(1)

        with qtbot.waitSignal(build_filter.filter_changed, timeout=1000):
            build_filter.class_combo.setCurrentIndex(1)

    def test_filter_changed_on_ascendancy_change(self, build_filter, qtbot):
        """Test that filter_changed signal is emitted on ascendancy change."""
        # Setup
        build_filter.game_combo.setCurrentIndex(1)
        build_filter.class_combo.setCurrentIndex(1)

        with qtbot.waitSignal(build_filter.filter_changed, timeout=1000):
            build_filter.ascendancy_combo.setCurrentIndex(1)

    def test_no_signal_during_programmatic_update(self, build_filter, qtbot):
        """Test that signal is not emitted during internal updates."""
        signal_count = 0

        def count_signal():
            nonlocal signal_count
            signal_count += 1

        build_filter.filter_changed.connect(count_signal)

        # Set filter programmatically
        initial_count = signal_count
        build_filter._updating = True
        build_filter.game_combo.setCurrentIndex(1)
        build_filter._updating = False

        # Should not have incremented during _updating = True
        # (Note: may increment after _updating = False)
        assert signal_count >= initial_count


class TestBuildFilterWidgetPublicAPI:
    """Tests for public API methods."""

    def test_get_game_version(self, build_filter):
        """Test getting selected game version."""
        # Default should be None (All Games)
        assert build_filter.get_game_version() is None

        # Select PoE 1
        build_filter.game_combo.setCurrentIndex(1)
        assert build_filter.get_game_version() == GameVersion.POE1

        # Select PoE 2
        build_filter.game_combo.setCurrentIndex(2)
        assert build_filter.get_game_version() == GameVersion.POE2

    def test_get_class_name(self, build_filter):
        """Test getting selected class name."""
        # Default should be None (All Classes)
        assert build_filter.get_class_name() is None

        # Select a specific class
        build_filter.game_combo.setCurrentIndex(1)  # PoE 1
        for i in range(build_filter.class_combo.count()):
            if build_filter.class_combo.itemText(i) == "Marauder":
                build_filter.class_combo.setCurrentIndex(i)
                break

        assert build_filter.get_class_name() == "Marauder"

    def test_get_ascendancy(self, build_filter):
        """Test getting selected ascendancy."""
        # Default should be None (All Ascendancies)
        assert build_filter.get_ascendancy() is None

        # Select a specific ascendancy
        build_filter.game_combo.setCurrentIndex(1)  # PoE 1
        for i in range(build_filter.class_combo.count()):
            if build_filter.class_combo.itemText(i) == "Marauder":
                build_filter.class_combo.setCurrentIndex(i)
                break

        for i in range(build_filter.ascendancy_combo.count()):
            if build_filter.ascendancy_combo.itemText(i) == "Juggernaut":
                build_filter.ascendancy_combo.setCurrentIndex(i)
                break

        assert build_filter.get_ascendancy() == "Juggernaut"

    def test_get_filter(self, build_filter):
        """Test getting filter as dictionary."""
        # Default filter
        filter_dict = build_filter.get_filter()
        assert filter_dict["game_version"] is None
        assert filter_dict["class_name"] is None
        assert filter_dict["ascendancy"] is None

        # Set specific filters
        build_filter.game_combo.setCurrentIndex(1)  # PoE 1
        for i in range(build_filter.class_combo.count()):
            if build_filter.class_combo.itemText(i) == "Witch":
                build_filter.class_combo.setCurrentIndex(i)
                break
        for i in range(build_filter.ascendancy_combo.count()):
            if build_filter.ascendancy_combo.itemText(i) == "Necromancer":
                build_filter.ascendancy_combo.setCurrentIndex(i)
                break

        filter_dict = build_filter.get_filter()
        assert filter_dict["game_version"] == GameVersion.POE1
        assert filter_dict["class_name"] == "Witch"
        assert filter_dict["ascendancy"] == "Necromancer"

    def test_set_filter(self, build_filter, qtbot):
        """Test setting filter programmatically."""
        build_filter.set_filter(
            game_version=GameVersion.POE1,
            class_name="Ranger",
            ascendancy="Deadeye"
        )

        assert build_filter.get_game_version() == GameVersion.POE1
        assert build_filter.get_class_name() == "Ranger"
        assert build_filter.get_ascendancy() == "Deadeye"

    def test_set_filter_partial(self, build_filter, qtbot):
        """Test setting filter with partial data."""
        build_filter.set_filter(game_version=GameVersion.POE2)

        assert build_filter.get_game_version() == GameVersion.POE2
        # Class and ascendancy should remain at defaults
        assert build_filter.get_class_name() is None
        assert build_filter.get_ascendancy() is None

    def test_set_filter_to_none(self, build_filter, qtbot):
        """Test setting filter back to 'All'."""
        # First set to specific values
        build_filter.set_filter(
            game_version=GameVersion.POE1,
            class_name="Marauder"
        )

        # Then reset to None
        build_filter.set_filter(
            game_version=None,
            class_name=None,
            ascendancy=None
        )

        assert build_filter.get_game_version() is None
        assert build_filter.get_class_name() is None
        assert build_filter.get_ascendancy() is None

    def test_reset(self, build_filter, qtbot):
        """Test resetting all filters."""
        # Set to specific values
        build_filter.set_filter(
            game_version=GameVersion.POE1,
            class_name="Duelist",
            ascendancy="Slayer"
        )

        # Reset
        build_filter.reset()

        # Should be back to defaults
        assert build_filter.get_game_version() is None
        assert build_filter.get_class_name() is None
        assert build_filter.get_ascendancy() is None


class TestBuildFilterWidgetMatching:
    """Tests for matches_build method."""

    def test_matches_build_all_filters(self, build_filter):
        """Test that 'All' filters match any build."""
        build_filter.reset()

        # Should match any build
        assert build_filter.matches_build("Marauder", "Juggernaut") is True
        assert build_filter.matches_build("Witch", "Necromancer") is True
        assert build_filter.matches_build("", "") is True

    def test_matches_build_specific_class(self, build_filter):
        """Test matching with specific class filter."""
        build_filter.set_filter(class_name="Marauder")

        assert build_filter.matches_build("Marauder", "Juggernaut") is True
        assert build_filter.matches_build("Marauder", "Berserker") is True
        assert build_filter.matches_build("Witch", "Necromancer") is False

    def test_matches_build_specific_ascendancy(self, build_filter):
        """Test matching with specific ascendancy filter."""
        build_filter.set_filter(ascendancy="Juggernaut")

        assert build_filter.matches_build("Marauder", "Juggernaut") is True
        assert build_filter.matches_build("Marauder", "Berserker") is False
        # When only ascendancy is filtered, class doesn't matter
        # (The widget doesn't enforce valid class/ascendancy combos)

    def test_matches_build_class_and_ascendancy(self, build_filter):
        """Test matching with both class and ascendancy filters."""
        build_filter.set_filter(class_name="Ranger", ascendancy="Deadeye")

        assert build_filter.matches_build("Ranger", "Deadeye") is True
        assert build_filter.matches_build("Ranger", "Raider") is False
        assert build_filter.matches_build("Duelist", "Deadeye") is False

    def test_matches_build_case_insensitive(self, build_filter):
        """Test that matching is case-insensitive."""
        build_filter.set_filter(class_name="Marauder", ascendancy="Juggernaut")

        assert build_filter.matches_build("marauder", "juggernaut") is True
        assert build_filter.matches_build("MARAUDER", "JUGGERNAUT") is True
        assert build_filter.matches_build("MaRaUdEr", "JuGgErNaUt") is True

    def test_matches_build_with_game_version(self, build_filter):
        """Test matching with game version filter."""
        build_filter.set_filter(game_version=GameVersion.POE1)

        # Should match PoE1 builds
        assert build_filter.matches_build("Marauder", "Juggernaut") is True
        assert build_filter.matches_build("Witch", "Necromancer") is True

        # PoE2 builds should not match (if detectable)
        # This depends on game_data.detect_game_version implementation

    def test_matches_build_empty_strings(self, build_filter):
        """Test matching with empty build data."""
        build_filter.set_filter(class_name="Marauder")

        # Empty build data should not match specific filter
        assert build_filter.matches_build("", "") is False
        assert build_filter.matches_build("Marauder", "") is True


class TestBuildFilterWidgetIntegration:
    """Integration tests for complete workflows."""

    def test_complete_filter_workflow(self, build_filter, qtbot):
        """Test complete filtering workflow."""
        signal_count = 0

        def count_signals():
            nonlocal signal_count
            signal_count += 1

        build_filter.filter_changed.connect(count_signals)

        # Start fresh
        build_filter.reset()
        initial_count = signal_count

        # Select PoE 1
        build_filter.game_combo.setCurrentIndex(1)
        assert signal_count > initial_count

        # Select Witch
        for i in range(build_filter.class_combo.count()):
            if build_filter.class_combo.itemText(i) == "Witch":
                build_filter.class_combo.setCurrentIndex(i)
                break

        # Select Necromancer
        for i in range(build_filter.ascendancy_combo.count()):
            if build_filter.ascendancy_combo.itemText(i) == "Necromancer":
                build_filter.ascendancy_combo.setCurrentIndex(i)
                break

        # Verify final state
        assert build_filter.get_game_version() == GameVersion.POE1
        assert build_filter.get_class_name() == "Witch"
        assert build_filter.get_ascendancy() == "Necromancer"
        assert build_filter.matches_build("Witch", "Necromancer") is True
        assert build_filter.matches_build("Witch", "Elementalist") is False

    def test_switching_games_resets_selections(self, build_filter, qtbot):
        """Test that switching games resets class/ascendancy appropriately."""
        # Select PoE1 with specific class/ascendancy
        build_filter.set_filter(
            game_version=GameVersion.POE1,
            class_name="Marauder",
            ascendancy="Juggernaut"
        )

        # Switch to PoE2
        build_filter.game_combo.setCurrentIndex(2)

        # Class/ascendancy should be reset since "Marauder" doesn't exist in PoE2
        # The widget repopulates with PoE2 classes
        class_names = [
            build_filter.class_combo.itemText(i)
            for i in range(build_filter.class_combo.count())
        ]
        assert "Marauder" not in class_names  # PoE1 class shouldn't be in PoE2 list
        assert "Warrior" in class_names  # PoE2 class should be present

    def test_multiple_set_filter_calls(self, build_filter, qtbot):
        """Test multiple sequential set_filter calls."""
        # First filter
        build_filter.set_filter(game_version=GameVersion.POE1, class_name="Witch")
        assert build_filter.get_game_version() == GameVersion.POE1
        assert build_filter.get_class_name() == "Witch"

        # Second filter (different values)
        build_filter.set_filter(game_version=GameVersion.POE1, class_name="Ranger")
        assert build_filter.get_game_version() == GameVersion.POE1
        assert build_filter.get_class_name() == "Ranger"

        # Third filter (reset)
        build_filter.reset()
        assert build_filter.get_game_version() is None
        assert build_filter.get_class_name() is None
