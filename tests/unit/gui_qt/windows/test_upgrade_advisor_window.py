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
    config.ai_provider = "gemini"
    config.has_ai_configured.return_value = True
    config.get_ai_api_key.return_value = "test-api-key"  # Default: API key exists
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

    def test_buttons_disabled_when_ai_not_configured(self, window, mock_config):
        """Buttons disabled when AI not configured."""
        # Mock no API key for the selected provider
        mock_config.get_ai_api_key.return_value = None
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


# =============================================================================
# Cache Tests
# =============================================================================


class TestItemHash:
    """Tests for item hash computation."""

    def test_compute_hash_with_item(self, window):
        """Hash is computed for items with data."""
        item_data = MagicMock()
        item_data.name = "Test Helmet"
        item_data.base_type = "Royal Burgonet"
        item_data.rarity = "RARE"
        item_data.item_level = 85
        item_data.implicit_mods = ["+30 to Maximum Life"]
        item_data.explicit_mods = ["+80 to Maximum Life"]

        hash1 = window._compute_item_hash(item_data)

        assert len(hash1) == 16  # MD5 truncated
        assert hash1 != "empty"

    def test_compute_hash_empty_item(self, window):
        """Hash is 'empty' for None items."""
        assert window._compute_item_hash(None) == "empty"

    def test_same_item_same_hash(self, window):
        """Same item produces same hash."""
        item_data = MagicMock()
        item_data.name = "Test"
        item_data.base_type = "Base"
        item_data.rarity = "RARE"
        item_data.item_level = 80
        item_data.implicit_mods = []
        item_data.explicit_mods = ["+50 Life"]

        hash1 = window._compute_item_hash(item_data)
        hash2 = window._compute_item_hash(item_data)

        assert hash1 == hash2

    def test_different_mods_different_hash(self, window):
        """Different mods produce different hash."""
        item1 = MagicMock()
        item1.name = "Test"
        item1.base_type = "Base"
        item1.rarity = "RARE"
        item1.item_level = 80
        item1.implicit_mods = []
        item1.explicit_mods = ["+50 Life"]

        item2 = MagicMock()
        item2.name = "Test"
        item2.base_type = "Base"
        item2.rarity = "RARE"
        item2.item_level = 80
        item2.implicit_mods = []
        item2.explicit_mods = ["+100 Life"]  # Different mod

        hash1 = window._compute_item_hash(item1)
        hash2 = window._compute_item_hash(item2)

        assert hash1 != hash2


class TestCaching:
    """Tests for advice caching."""

    def test_set_database(self, window):
        """Database can be set."""
        mock_db = MagicMock()
        window.set_database(mock_db)
        assert window._db == mock_db

    def test_save_to_cache(self, window):
        """Advice is saved to database."""
        mock_db = MagicMock()
        window.set_database(mock_db)
        window._item_hashes["Helmet"] = "abc123"

        window._save_to_cache("Helmet", "Test advice", "gemini")

        mock_db.save_upgrade_advice.assert_called_once_with(
            profile_name="Test Character",
            slot="Helmet",
            item_hash="abc123",
            advice_text="Test advice",
            ai_model="gemini",
        )

    def test_show_result_saves_to_cache(self, window):
        """show_analysis_result saves to cache."""
        mock_db = MagicMock()
        window.set_database(mock_db)
        window._item_hashes["Helmet"] = "abc123"

        window.show_analysis_result("Helmet", "Test result", "claude")

        mock_db.save_upgrade_advice.assert_called_once()

    def test_load_cached_advice(self, qtbot, mock_config, mock_character_manager):
        """Cached advice is loaded on window creation."""
        mock_db = MagicMock()

        # Pre-configure cache data
        mock_db.get_all_upgrade_advice.return_value = {
            "Helmet": {
                "advice_text": "Cached advice for helmet",
                "ai_model": "gemini",
                "created_at": "2025-01-01 00:00:00",
                "item_hash": "test_hash",
            }
        }

        window = UpgradeAdvisorWindow(
            config=mock_config,
            character_manager=mock_character_manager,
        )
        qtbot.addWidget(window)

        # Set database and compute matching hash
        window.set_database(mock_db)

        # Force the hash to match
        window._item_hashes["Helmet"] = "test_hash"
        window._load_cached_advice()

        # Should have loaded cached advice
        assert "Helmet" in window._analysis_results
        assert window._analysis_results["Helmet"] == "Cached advice for helmet"
        assert "Helmet" in window._cached_slots

    def test_cache_invalidated_on_item_change(self, qtbot, mock_config, mock_character_manager):
        """Cache is invalidated when item hash changes."""
        mock_db = MagicMock()
        mock_db.get_all_upgrade_advice.return_value = {
            "Helmet": {
                "advice_text": "Old cached advice",
                "ai_model": "gemini",
                "created_at": "2025-01-01 00:00:00",
                "item_hash": "old_hash",  # Different from current
            }
        }

        window = UpgradeAdvisorWindow(
            config=mock_config,
            character_manager=mock_character_manager,
        )
        qtbot.addWidget(window)
        window.set_database(mock_db)

        # Current item has different hash
        window._item_hashes["Helmet"] = "new_hash"
        window._load_cached_advice()

        # Should NOT have loaded stale cache
        assert "Helmet" not in window._analysis_results
        assert "Helmet" not in window._cached_slots

    def test_cached_status_shows_in_tree(self, qtbot, mock_config, mock_character_manager):
        """Cached slots show 'Cached' status on load from DB."""
        mock_db = MagicMock()

        # Return cached data that matches the item hash
        mock_db.get_all_upgrade_advice.return_value = {
            "Helmet": {
                "advice_text": "Cached advice",
                "ai_model": "gemini",
                "created_at": "2025-01-01 00:00:00",
                "item_hash": "placeholder",  # Will be replaced
            }
        }

        window = UpgradeAdvisorWindow(
            config=mock_config,
            character_manager=mock_character_manager,
        )
        qtbot.addWidget(window)

        # Get the actual hash that was computed for Helmet
        actual_hash = window._item_hashes.get("Helmet", "")
        mock_db.get_all_upgrade_advice.return_value["Helmet"]["item_hash"] = actual_hash

        # Now set database and reload
        window.set_database(mock_db)
        window._load_cached_advice()

        # Refresh tree to show cached status
        window.equipment_tree.clear()
        items = getattr(mock_character_manager.get_active_profile().build, "items", {})
        for slot in EQUIPMENT_SLOTS:
            window._add_slot_row(slot, items.get(slot))

        # Find helmet row and check status
        for i in range(window.equipment_tree.topLevelItemCount()):
            item = window.equipment_tree.topLevelItem(i)
            if item.text(0) == "Helmet":
                assert item.text(2) == "Cached"
                break
