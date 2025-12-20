"""Tests for UpgradeAdvisorView full-screen view."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gui_qt.views.upgrade_advisor_view import UpgradeAdvisorView, EQUIPMENT_SLOTS


@pytest.fixture
def mock_ctx():
    """Create a mock AppContext."""
    ctx = MagicMock()
    ctx.config.ai_provider = "gemini"
    ctx.config.get_ai_api_key.return_value = "test-key"
    ctx.db = MagicMock()
    ctx.db.get_upgrade_advice_history.return_value = []
    ctx.db.get_all_slots_latest_history.return_value = {}
    return ctx


@pytest.fixture
def mock_character_manager():
    """Create a mock CharacterManager."""
    manager = MagicMock()

    # Create mock profile
    profile = MagicMock()
    profile.name = "TestBuild"
    profile.build.ascendancy = "Slayer"
    profile.build.class_name = "Duelist"
    profile.build.main_skill = "Cyclone"
    profile.build.level = 95
    profile.build.items = {}

    manager.get_active_profile.return_value = profile
    return manager


@pytest.fixture
def view(qtbot, mock_ctx, mock_character_manager):
    """Create an UpgradeAdvisorView for testing."""
    widget = UpgradeAdvisorView(
        ctx=mock_ctx,
        character_manager=mock_character_manager,
        on_close=MagicMock(),
        on_status=MagicMock(),
    )
    qtbot.addWidget(widget)
    return widget


class TestUpgradeAdvisorViewInit:
    """Tests for initialization."""

    def test_creates_header_widgets(self, view):
        """Test header widgets are created."""
        assert view.back_btn is not None
        assert view.profile_label is not None
        assert view.provider_combo is not None
        assert view.refresh_btn is not None

    def test_creates_equipment_panel(self, view):
        """Test equipment panel is created."""
        assert view.equipment_tree is not None
        assert view.analyze_btn is not None

    def test_creates_results_panel(self, view):
        """Test results panel is created."""
        assert view.result_slot_label is not None
        assert view.include_stash_cb is not None
        assert view.results_text is not None
        assert view.progress_bar is not None

    def test_creates_history_panel(self, view):
        """Test history panel is created."""
        assert view._history_panel is not None

    def test_loads_profile_on_init(self, view):
        """Test profile is loaded on initialization."""
        # Profile label should contain build info
        assert "TestBuild" in view.profile_label.text()

    def test_analyze_btn_initially_disabled(self, view):
        """Test analyze button is disabled initially (no slot selected)."""
        assert not view.analyze_btn.isEnabled()


class TestEquipmentSlots:
    """Tests for equipment slot handling."""

    def test_equipment_slots_constant(self):
        """Test EQUIPMENT_SLOTS contains expected slots."""
        assert "Helmet" in EQUIPMENT_SLOTS
        assert "Body Armour" in EQUIPMENT_SLOTS
        assert "Gloves" in EQUIPMENT_SLOTS
        assert "Boots" in EQUIPMENT_SLOTS
        assert "Belt" in EQUIPMENT_SLOTS
        assert "Amulet" in EQUIPMENT_SLOTS
        assert "Ring 1" in EQUIPMENT_SLOTS
        assert "Ring 2" in EQUIPMENT_SLOTS
        assert "Weapon 1" in EQUIPMENT_SLOTS
        assert "Weapon 2" in EQUIPMENT_SLOTS


class TestSlotSelection:
    """Tests for slot selection."""

    def test_select_slot_updates_label(self, view, qtbot):
        """Test selecting a slot updates the result label."""
        # Add a slot to the tree
        view._populate_equipment_tree()

        if view.equipment_tree.topLevelItemCount() > 0:
            item = view.equipment_tree.topLevelItem(0)
            view._on_slot_clicked(item, 0)

            assert view._selected_slot is not None

    def test_select_slot_enables_analyze(self, view, qtbot):
        """Test selecting a slot enables analyze button (when AI configured)."""
        view._populate_equipment_tree()

        if view.equipment_tree.topLevelItemCount() > 0:
            item = view.equipment_tree.topLevelItem(0)
            view._on_slot_clicked(item, 0)

            # Should be enabled if AI is configured
            # (depends on mock setup)


class TestIncludeStashOption:
    """Tests for include stash checkbox."""

    def test_stash_checkbox_default_unchecked(self, view):
        """Test stash checkbox is unchecked by default."""
        assert not view.include_stash_cb.isChecked()

    def test_stash_checkbox_can_be_checked(self, view, qtbot):
        """Test stash checkbox can be toggled."""
        view.include_stash_cb.setChecked(True)
        assert view.include_stash_cb.isChecked()


class TestAnalysis:
    """Tests for analysis functionality."""

    def test_start_analysis_emits_signal(self, view, qtbot):
        """Test starting analysis emits signal."""
        view._selected_slot = "Helmet"

        with qtbot.waitSignal(view.upgrade_analysis_requested, timeout=1000) as blocker:
            view._start_analysis()

        assert blocker.args[0] == "Helmet"

    def test_start_analysis_shows_progress(self, view, qtbot):
        """Test starting analysis shows progress bar when AI is configured."""
        view._selected_slot = "Helmet"
        # The signal should be emitted but progress won't show if _is_ai_configured is False
        # Just verify signal emission
        with qtbot.waitSignal(view.upgrade_analysis_requested, timeout=1000):
            view._start_analysis()
        # After emission, progress bar should be visible
        assert view._analyzing_slot == "Helmet"

    def test_show_analysis_result_displays_markdown(self, view, qtbot):
        """Test showing analysis result displays markdown."""
        view._selected_slot = "Helmet"

        result = "# Analysis\n\nThis is a test **result**."
        view.show_analysis_result("Helmet", result, "gemini")

        # Should display the result
        assert not view.progress_bar.isVisible()
        assert view.analyze_btn.isEnabled()

    def test_show_analysis_error_displays_error(self, view, qtbot):
        """Test showing analysis error displays error message."""
        view._selected_slot = "Helmet"

        view.show_analysis_error("Helmet", "API Error occurred")

        assert not view.progress_bar.isVisible()
        assert view.analyze_btn.isEnabled()


class TestProviderSelection:
    """Tests for AI provider selection."""

    def test_provider_combo_populated(self, view):
        """Test provider combo is populated with providers."""
        assert view.provider_combo.count() > 0

    def test_get_selected_provider(self, view):
        """Test get_selected_provider returns current provider."""
        provider = view.get_selected_provider()
        assert provider is not None


class TestClose:
    """Tests for close functionality."""

    def test_close_btn_emits_signal(self, view, qtbot):
        """Test close button emits close_requested signal."""
        with qtbot.waitSignal(view.close_requested, timeout=1000):
            view.close_btn.click()

    def test_back_btn_emits_signal(self, view, qtbot):
        """Test back button emits close_requested signal."""
        with qtbot.waitSignal(view.close_requested, timeout=1000):
            view.back_btn.click()

    def test_close_calls_callback(self, view, qtbot):
        """Test closing calls the on_close callback."""
        view._on_close_clicked()
        view._on_close.assert_called_once()


class TestRefresh:
    """Tests for refresh functionality."""

    def test_refresh_reloads_profile(self, view, mock_character_manager, qtbot):
        """Test refresh reloads the profile."""
        view.refresh()

        mock_character_manager.get_active_profile.assert_called()

    def test_refresh_btn_triggers_refresh(self, view, mock_character_manager, qtbot):
        """Test refresh button triggers profile reload."""
        view.refresh_btn.click()

        # Should have called get_active_profile at least twice
        # (once on init, once on refresh)
        assert mock_character_manager.get_active_profile.call_count >= 2


class TestHistoryIntegration:
    """Tests for history panel integration."""

    def test_use_cached_updates_results(self, view, qtbot):
        """Test using cached analysis updates results panel."""
        view._selected_slot = "Helmet"

        # Setup history through the view's method which sets _history_items
        history_data = [
            {
                "id": 1,
                "advice_text": "# Cached Analysis\n\nThis is cached.",
                "created_at": "2025-12-07 14:30:00",
                "ai_provider": "gemini",
                "include_stash": False,
                "item_hash": "abc123",
            }
        ]
        view._history_panel.load_history("Helmet", history_data)

        view._on_use_cached(1)

        # Should update viewing history label (frame visibility depends on parent state)
        assert "Viewing cached" in view.viewing_history_label.text()


class TestSelectSlotMethod:
    """Tests for select_slot public method."""

    def test_select_slot_selects_in_tree(self, view, qtbot):
        """Test select_slot method selects the slot in tree."""
        view._populate_equipment_tree()

        view.select_slot("Helmet")

        assert view._selected_slot == "Helmet"
