"""Tests for UpgradeAdvisorWindow."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

from gui_qt.windows.upgrade_advisor_window import (
    UpgradeAdvisorWindow,
    EQUIPMENT_SLOTS,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock()
    config.league = "Settlers"
    config.has_ai_configured.return_value = True
    config.data = {"stash": {"account_name": "TestAccount"}}
    return config


@pytest.fixture
def mock_character_manager():
    """Create mock character manager."""
    manager = MagicMock()

    # Mock profile
    profile = MagicMock()
    profile.name = "Test Character"

    # Mock build
    build = MagicMock()
    build.class_name = "Marauder"
    build.ascendancy = "Juggernaut"
    build.level = 90
    build.main_skill = "Cyclone"

    # Mock items
    helmet = MagicMock()
    helmet.name = "Test Helmet"
    helmet.rarity = "RARE"
    helmet.base_type = "Royal Burgonet"
    helmet.item_level = 85
    helmet.implicit_mods = ["+30 to Maximum Life"]
    helmet.explicit_mods = ["+80 to Maximum Life", "+40% Fire Resistance"]

    build.items = {
        "Helmet": helmet,
        "Body Armour": None,  # Empty slot
    }

    profile.build = build
    manager.get_active_profile.return_value = profile

    return manager


@pytest.fixture
def window(qtbot, mock_config, mock_character_manager):
    """Create UpgradeAdvisorWindow instance."""
    window = UpgradeAdvisorWindow(
        config=mock_config,
        character_manager=mock_character_manager,
    )
    qtbot.addWidget(window)
    return window


# =============================================================================
# Test Window Creation
# =============================================================================


class TestUpgradeAdvisorWindowInit:
    """Tests for window initialization."""

    def test_window_title(self, window):
        """Window has correct title."""
        assert window.windowTitle() == "Upgrade Advisor"

    def test_minimum_size(self, window):
        """Window has minimum size set."""
        assert window.minimumWidth() >= 800
        assert window.minimumHeight() >= 600

    def test_profile_loaded(self, window):
        """Profile is loaded on init."""
        assert "Test Character" in window.profile_label.text()

    def test_equipment_tree_populated(self, window):
        """Equipment tree is populated with slots."""
        assert window.equipment_tree.topLevelItemCount() == len(EQUIPMENT_SLOTS)


class TestEquipmentDisplay:
    """Tests for equipment display."""

    def test_slot_names_displayed(self, window):
        """All equipment slots are displayed."""
        displayed_slots = []
        for i in range(window.equipment_tree.topLevelItemCount()):
            item = window.equipment_tree.topLevelItem(i)
            displayed_slots.append(item.text(0))

        for slot in EQUIPMENT_SLOTS:
            assert slot in displayed_slots

    def test_item_name_displayed(self, window):
        """Item names are displayed for equipped items."""
        # Find the Helmet row
        for i in range(window.equipment_tree.topLevelItemCount()):
            item = window.equipment_tree.topLevelItem(i)
            if item.text(0) == "Helmet":
                assert "Test Helmet" in item.text(1)
                break
        else:
            pytest.fail("Helmet slot not found")

    def test_empty_slot_displayed(self, window):
        """Empty slots show (Empty) placeholder."""
        # Find the Body Armour row
        for i in range(window.equipment_tree.topLevelItemCount()):
            item = window.equipment_tree.topLevelItem(i)
            if item.text(0) == "Body Armour":
                assert "(Empty)" in item.text(1)
                break
        else:
            pytest.fail("Body Armour slot not found")

    def test_item_data_stored(self, window):
        """Item data is stored in UserRole."""
        for i in range(window.equipment_tree.topLevelItemCount()):
            item = window.equipment_tree.topLevelItem(i)
            if item.text(0) == "Helmet":
                data = item.data(0, Qt.ItemDataRole.UserRole)
                assert data is not None
                assert data.name == "Test Helmet"
                break


class TestButtonStates:
    """Tests for button enabled states."""

    def test_analyze_selected_disabled_initially(self, window):
        """Analyze selected button disabled when no selection."""
        assert not window.analyze_selected_btn.isEnabled()

    def test_analyze_selected_enabled_on_click(self, qtbot, window):
        """Analyze selected button enabled after selecting a slot."""
        # Click on first item
        first_item = window.equipment_tree.topLevelItem(0)
        window.equipment_tree.setCurrentItem(first_item)
        window._on_slot_clicked(first_item, 0)

        # Button should be enabled (if AI is configured)
        window.set_ai_configured_callback(lambda: True)
        window._on_slot_clicked(first_item, 0)
        assert window.analyze_selected_btn.isEnabled()

    def test_buttons_disabled_when_ai_not_configured(self, window):
        """Buttons disabled when AI not configured."""
        window.set_ai_configured_callback(lambda: False)
        window._update_button_states()

        assert not window.analyze_all_btn.isEnabled()


class TestSignals:
    """Tests for signal emission."""

    def test_upgrade_analysis_requested_signal(self, qtbot, window):
        """Signal emitted when analysis requested."""
        window.set_ai_configured_callback(lambda: True)

        # Select first slot
        first_item = window.equipment_tree.topLevelItem(0)
        window.equipment_tree.setCurrentItem(first_item)

        # Connect signal
        signal_received = []

        def on_signal(slot, item_text):
            signal_received.append((slot, item_text))

        window.upgrade_analysis_requested.connect(on_signal)

        # Trigger analysis
        window._on_analyze_selected()

        assert len(signal_received) == 1
        assert signal_received[0][0] == EQUIPMENT_SLOTS[0]


class TestAnalysisResults:
    """Tests for displaying analysis results."""

    def test_show_analysis_result(self, window):
        """Result is displayed correctly."""
        result_text = "## BEST\n**Siege Dome** from Stash Tab 1"
        window.show_analysis_result("Helmet", result_text)

        assert "Helmet" in window.result_slot_label.text()
        assert window._analysis_results.get("Helmet") == result_text

    def test_show_analysis_error(self, window):
        """Error is displayed correctly."""
        window.show_analysis_error("Helmet", "API timeout")

        assert "Error" in window.result_slot_label.text()
        assert "API timeout" in window.results_text.toPlainText()

    def test_progress_bar_hidden_after_result(self, window):
        """Progress bar hidden after result received."""
        # Start analysis (shows progress)
        window._analyzing_slot = "Helmet"
        window.progress_bar.setVisible(True)

        # Complete analysis
        window.show_analysis_result("Helmet", "Result text")

        assert not window.progress_bar.isVisible()

    def test_status_updated_in_tree(self, window):
        """Tree status column updated after analysis."""
        window.show_analysis_result("Helmet", "Result")

        # Find helmet row and check status
        for i in range(window.equipment_tree.topLevelItemCount()):
            item = window.equipment_tree.topLevelItem(i)
            if item.text(0) == "Helmet":
                assert item.text(2) == "Analyzed"
                break


class TestItemTextGeneration:
    """Tests for item text generation."""

    def test_generate_item_text_basic(self, window):
        """Basic item text generation."""
        item_data = MagicMock()
        item_data.rarity = "RARE"
        item_data.name = "Test Item"
        item_data.base_type = "Royal Burgonet"
        item_data.item_level = 85
        item_data.implicit_mods = []
        item_data.explicit_mods = ["+80 to Life"]

        text = window._generate_item_text(item_data)

        assert "Rarity: Rare" in text
        assert "Test Item" in text
        assert "Royal Burgonet" in text
        assert "+80 to Life" in text

    def test_generate_item_text_filters_metadata(self, window):
        """Metadata mods are filtered out."""
        item_data = MagicMock()
        item_data.rarity = "RARE"
        item_data.name = "Test"
        item_data.base_type = "Helmet"
        item_data.item_level = 85
        item_data.implicit_mods = []
        item_data.explicit_mods = [
            "+80 to Life",
            "Armour: 500",
            "ArmourBasePercentile: 100",
        ]

        text = window._generate_item_text(item_data)

        assert "+80 to Life" in text
        assert "Armour: 500" not in text
        assert "ArmourBasePercentile" not in text


class TestAnalyzeSlot:
    """Tests for programmatic slot analysis."""

    def test_analyze_slot_selects_and_starts(self, qtbot, window):
        """analyze_slot method selects slot and starts analysis."""
        window.set_ai_configured_callback(lambda: True)

        signal_received = []
        window.upgrade_analysis_requested.connect(
            lambda s, t: signal_received.append(s)
        )

        window.analyze_slot("Helmet")

        assert len(signal_received) == 1
        assert signal_received[0] == "Helmet"

    def test_analyze_slot_invalid_slot(self, window):
        """analyze_slot with invalid slot does nothing."""
        window.set_ai_configured_callback(lambda: True)

        signal_received = []
        window.upgrade_analysis_requested.connect(
            lambda s, t: signal_received.append(s)
        )

        window.analyze_slot("InvalidSlot")

        assert len(signal_received) == 0


# =============================================================================
# Test No Profile Scenario
# =============================================================================


class TestNoProfile:
    """Tests when no profile is loaded."""

    def test_no_active_profile(self, qtbot, mock_config):
        """Window handles no active profile."""
        manager = MagicMock()
        manager.get_active_profile.return_value = None

        window = UpgradeAdvisorWindow(
            config=mock_config,
            character_manager=manager,
        )
        qtbot.addWidget(window)

        assert "No active profile" in window.profile_label.text()
        assert window.equipment_tree.topLevelItemCount() == 0
