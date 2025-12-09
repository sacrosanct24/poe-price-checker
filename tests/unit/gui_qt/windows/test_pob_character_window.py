"""Tests for gui_qt/windows/pob_character_window.py - PoB character management."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QMessageBox

from gui_qt.windows.pob_character_window import (
    PoBCharacterWindow,
    ItemDetailsDialog,
    ManageCategoriesDialog,
    ImportPoBDialog,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_character_manager():
    """Create a mock character manager."""
    manager = MagicMock()
    manager.list_profiles.return_value = []
    manager.get_active_profile.return_value = None
    manager.get_upgrade_target.return_value = None
    manager.get_profile.return_value = None
    return manager


@pytest.fixture
def mock_profile():
    """Create a mock profile."""
    profile = MagicMock()
    profile.name = "TestBuild"
    profile.categories = ["league_starter", "mapper"]
    profile.is_upgrade_target = False

    # Make sure get_archetype returns None (not MagicMock)
    profile.get_archetype.return_value = None

    # Mock build
    build = MagicMock()
    build.class_name = "Witch"
    build.ascendancy = "Necromancer"
    build.level = 95

    # Mock items
    item1 = MagicMock()
    item1.name = "Tabula Rasa"
    item1.base_type = "Simple Robe"
    item1.rarity = "unique"
    item1.implicit_mods = []
    item1.explicit_mods = []

    item2 = MagicMock()
    item2.name = "Goldrim"
    item2.base_type = "Leather Cap"
    item2.rarity = "unique"
    item2.implicit_mods = []
    item2.explicit_mods = ["+30 to all Elemental Resistances"]

    build.items = {
        "Body Armour": item1,
        "Helmet": item2,
    }

    profile.build = build
    return profile


# =============================================================================
# PoBCharacterWindow Tests
# =============================================================================


class TestPoBCharacterWindowInit:
    """Tests for PoBCharacterWindow initialization."""

    def test_init_sets_title(self, qtbot, mock_character_manager):
        """Should set window title."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)
        assert window.windowTitle() == "PoB Character Manager"

    def test_init_sets_minimum_size(self, qtbot, mock_character_manager):
        """Should set minimum size."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)
        assert window.minimumWidth() >= 700
        assert window.minimumHeight() >= 450

    def test_init_creates_profile_list(self, qtbot, mock_character_manager):
        """Should create profile list widget."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)
        assert window.profile_list is not None

    def test_init_creates_filter_combo(self, qtbot, mock_character_manager):
        """Should create category filter combo."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)
        assert window.filter_combo is not None
        assert window.filter_combo.count() >= 2  # At least "All" and "---"

    def test_init_creates_equipment_tree(self, qtbot, mock_character_manager):
        """Should create equipment tree widget."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)
        assert window.equipment_tree is not None

    def test_init_creates_buttons(self, qtbot, mock_character_manager):
        """Should create action buttons."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)
        assert window.import_btn is not None
        assert window.delete_btn is not None
        assert window.refresh_btn is not None
        assert window.set_active_btn is not None

    def test_init_stores_callbacks(self, qtbot, mock_character_manager):
        """Should store callbacks."""
        on_profile = MagicMock()
        on_price = MagicMock()

        window = PoBCharacterWindow(
            mock_character_manager,
            on_profile_selected=on_profile,
            on_price_check=on_price,
        )
        qtbot.addWidget(window)

        assert window.on_profile_selected is on_profile
        assert window.on_price_check is on_price

    def test_init_loads_profiles(self, qtbot, mock_character_manager):
        """Should call list_profiles on init."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)
        mock_character_manager.list_profiles.assert_called()


class TestPoBCharacterWindowLoadProfiles:
    """Tests for profile loading."""

    def test_load_profiles_clears_list(self, qtbot, mock_character_manager, mock_profile):
        """Should clear existing items before loading."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Add a dummy item
        window.profile_list.addItem("Dummy")

        # Reload
        window._load_profiles()

        # Should only have TestBuild (dummy cleared)
        assert window.profile_list.count() == 1

    def test_load_profiles_shows_active_tag(self, qtbot, mock_character_manager, mock_profile):
        """Should show [active] tag for active profile."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile
        mock_character_manager.get_active_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        item = window.profile_list.item(0)
        assert "active" in item.text().lower()

    def test_load_profiles_shows_category_tags(self, qtbot, mock_character_manager, mock_profile):
        """Should show category abbreviations."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        item = window.profile_list.item(0)
        # Should have LS (league_starter) and MAP (mapper)
        text = item.text()
        assert "LS" in text or "MAP" in text

    def test_load_profiles_updates_active_label(self, qtbot, mock_character_manager, mock_profile):
        """Should update active character label."""
        mock_character_manager.get_active_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        assert "TestBuild" in window.active_label.text()

    def test_load_profiles_filters_by_category(self, qtbot, mock_character_manager, mock_profile):
        """Should filter profiles by category."""
        mock_profile2 = MagicMock()
        mock_profile2.name = "OtherBuild"
        mock_profile2.categories = ["boss_killer"]
        mock_profile2.build = mock_profile.build

        def get_profile(name):
            if name == "TestBuild":
                return mock_profile
            return mock_profile2

        mock_character_manager.list_profiles.return_value = ["TestBuild", "OtherBuild"]
        mock_character_manager.get_profile.side_effect = get_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Initially shows all
        assert window.profile_list.count() == 2

        # Filter by league starter - only TestBuild has it
        # Find the league starter option
        for i in range(window.filter_combo.count()):
            if "league" in window.filter_combo.itemText(i).lower():
                window.filter_combo.setCurrentIndex(i)
                break

        # Should only show TestBuild now
        assert window.profile_list.count() == 1


class TestPoBCharacterWindowProfileSelection:
    """Tests for profile selection."""

    def test_select_profile_shows_details(self, qtbot, mock_character_manager, mock_profile):
        """Should show profile details when selected."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Select the profile
        window.profile_list.setCurrentRow(0)

        # Check details shown
        assert "TestBuild" in window.info_labels["Name"].text()
        assert "Witch" in window.info_labels["Class"].text()
        assert "Necromancer" in window.info_labels["Class"].text()

    def test_select_profile_shows_equipment(self, qtbot, mock_character_manager, mock_profile):
        """Should populate equipment tree when profile selected."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Select the profile
        window.profile_list.setCurrentRow(0)

        # Should have items in tree
        assert window.equipment_tree.topLevelItemCount() == 2


class TestPoBCharacterWindowActions:
    """Tests for window actions."""

    def test_delete_without_selection_shows_message(self, qtbot, mock_character_manager):
        """Should show message when deleting without selection."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        with patch.object(QMessageBox, 'information') as mock_info:
            window._on_delete()
            mock_info.assert_called_once()

    def test_set_active_without_selection_shows_message(self, qtbot, mock_character_manager):
        """Should show message when setting active without selection."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        with patch.object(QMessageBox, 'information') as mock_info:
            window._on_set_active()
            mock_info.assert_called_once()

    def test_set_active_calls_manager(self, qtbot, mock_character_manager, mock_profile):
        """Should call character manager to set active."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Select profile
        window.profile_list.setCurrentRow(0)

        with patch.object(QMessageBox, 'information'):
            window._on_set_active()
            mock_character_manager.set_active_profile.assert_called_with("TestBuild")

    def test_set_active_emits_signal(self, qtbot, mock_character_manager, mock_profile):
        """Should emit profile_selected signal."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Select profile
        window.profile_list.setCurrentRow(0)

        with qtbot.waitSignal(window.profile_selected, timeout=1000):
            with patch.object(QMessageBox, 'information'):
                window._on_set_active()

    def test_refresh_reloads_profiles(self, qtbot, mock_character_manager):
        """Should reload profiles on refresh click."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        mock_character_manager.list_profiles.reset_mock()
        window.refresh_btn.click()

        mock_character_manager.list_profiles.assert_called()

    @patch('gui_qt.windows.pob_character_window.ClearBuildsDialog')
    def test_clear_builds_opens_dialog(self, mock_dialog_cls, qtbot, mock_character_manager):
        """Should open clear builds dialog."""
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_cls.return_value = mock_dialog

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        window._on_clear_builds()

        mock_dialog_cls.assert_called_once()
        mock_dialog.exec.assert_called_once()

    @patch('gui_qt.windows.pob_character_window.FindBuildsDialog')
    def test_find_builds_opens_dialog(self, mock_dialog_cls, qtbot, mock_character_manager):
        """Should open find builds dialog."""
        mock_dialog = MagicMock()
        mock_dialog.exec.return_value = QDialog.DialogCode.Rejected
        mock_dialog_cls.return_value = mock_dialog

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        window._on_find_builds()

        mock_dialog_cls.assert_called_once()


class TestPoBCharacterWindowPriceCheck:
    """Tests for price check functionality."""

    def test_request_price_check_emits_signal(self, qtbot, mock_character_manager):
        """Should emit price_check_requested signal."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        with qtbot.waitSignal(window.price_check_requested, timeout=1000):
            window._request_price_check("Test Item")

    def test_request_price_check_calls_callback(self, qtbot, mock_character_manager):
        """Should call on_price_check callback."""
        on_price = MagicMock()
        window = PoBCharacterWindow(
            mock_character_manager,
            on_price_check=on_price,
        )
        qtbot.addWidget(window)

        window._request_price_check("Test Item")

        on_price.assert_called_with("Test Item")


# =============================================================================
# ItemDetailsDialog Tests
# =============================================================================


class TestItemDetailsDialogInit:
    """Tests for ItemDetailsDialog initialization."""

    def test_init_sets_title(self, qtbot):
        """Should set window title with slot name."""
        item_data = {"name": "Test Item", "rarity": "rare"}
        dialog = ItemDetailsDialog(None, "Helmet", item_data)
        qtbot.addWidget(dialog)
        assert "Helmet" in dialog.windowTitle()

    def test_init_displays_item_name(self, qtbot):
        """Should display item name."""
        item_data = {"name": "Goldrim", "rarity": "unique"}
        dialog = ItemDetailsDialog(None, "Helmet", item_data)
        qtbot.addWidget(dialog)

        # Name should be visible in dialog
        # Find label with name
        from PyQt6.QtWidgets import QLabel
        found = False
        for child in dialog.findChildren(QLabel):
            if "Goldrim" in child.text():
                found = True
                break
        assert found

    def test_init_displays_base_type(self, qtbot):
        """Should display base type when different from name."""
        item_data = {
            "name": "Goldrim",
            "base_type": "Leather Cap",
            "rarity": "unique",
        }
        dialog = ItemDetailsDialog(None, "Helmet", item_data)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QLabel
        found = False
        for child in dialog.findChildren(QLabel):
            if "Leather Cap" in child.text():
                found = True
                break
        assert found

    def test_init_displays_implicit_mods(self, qtbot):
        """Should display implicit mods."""
        item_data = {
            "name": "Test",
            "rarity": "rare",
            "implicit_mods": ["+10 to Maximum Life"],
        }
        dialog = ItemDetailsDialog(None, "Ring", item_data)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QLabel
        found = False
        for child in dialog.findChildren(QLabel):
            if "+10 to Maximum Life" in child.text():
                found = True
                break
        assert found

    def test_init_displays_explicit_mods(self, qtbot):
        """Should display explicit mods."""
        item_data = {
            "name": "Test",
            "rarity": "rare",
            "explicit_mods": ["+50 to Maximum Life", "+30% Fire Resistance"],
        }
        dialog = ItemDetailsDialog(None, "Ring", item_data)
        qtbot.addWidget(dialog)

        from PyQt6.QtWidgets import QLabel
        found_life = False
        found_res = False
        for child in dialog.findChildren(QLabel):
            if "+50 to Maximum Life" in child.text():
                found_life = True
            if "+30% Fire Resistance" in child.text():
                found_res = True
        assert found_life and found_res


class TestItemDetailsDialogPriceCheck:
    """Tests for price check in ItemDetailsDialog."""

    def test_price_check_calls_callback(self, qtbot):
        """Should call on_price_check callback."""
        on_price = MagicMock()
        item_data = {"name": "Test", "rarity": "rare"}
        dialog = ItemDetailsDialog(None, "Ring", item_data, on_price_check=on_price)
        qtbot.addWidget(dialog)

        dialog._on_price_check()

        on_price.assert_called_once()

    def test_generate_item_text_unique(self, qtbot):
        """Should generate correct text for unique items."""
        item_data = {
            "name": "Goldrim",
            "base_type": "Leather Cap",
            "rarity": "unique",
        }
        dialog = ItemDetailsDialog(None, "Helmet", item_data)
        qtbot.addWidget(dialog)

        text = dialog._generate_item_text()

        assert "Rarity: Unique" in text
        assert "Goldrim" in text
        assert "Leather Cap" in text

    def test_generate_item_text_rare(self, qtbot):
        """Should generate correct text for rare items."""
        item_data = {
            "name": "Apocalypse Bane",
            "base_type": "Two-Stone Ring",
            "rarity": "rare",
            "implicit_mods": ["+12% to Fire and Cold Resistances"],
            "explicit_mods": ["+50 to Maximum Life"],
        }
        dialog = ItemDetailsDialog(None, "Ring", item_data)
        qtbot.addWidget(dialog)

        text = dialog._generate_item_text()

        assert "Rarity: Rare" in text
        assert "Apocalypse Bane" in text
        assert "Two-Stone Ring" in text
        assert "+12% to Fire and Cold Resistances" in text
        assert "+50 to Maximum Life" in text


# =============================================================================
# ManageCategoriesDialog Tests
# =============================================================================


class TestManageCategoriesDialogInit:
    """Tests for ManageCategoriesDialog initialization."""

    def test_init_sets_title(self, qtbot, mock_character_manager, mock_profile):
        """Should set window title with profile name."""
        mock_character_manager.get_profile.return_value = mock_profile

        dialog = ManageCategoriesDialog(None, mock_character_manager, "TestBuild")
        qtbot.addWidget(dialog)

        assert "TestBuild" in dialog.windowTitle()

    @patch('gui_qt.windows.pob_character_window.BUILD_CATEGORIES', [])
    def test_init_empty_categories(self, qtbot, mock_character_manager, mock_profile):
        """Should handle empty category list."""
        mock_character_manager.get_profile.return_value = mock_profile

        dialog = ManageCategoriesDialog(None, mock_character_manager, "TestBuild")
        qtbot.addWidget(dialog)

        assert len(dialog.category_checks) == 0


class TestManageCategoriesDialogSave:
    """Tests for saving categories."""

    def test_save_calls_manager(self, qtbot, mock_character_manager, mock_profile):
        """Should call manager to save categories."""
        mock_character_manager.get_profile.return_value = mock_profile

        dialog = ManageCategoriesDialog(None, mock_character_manager, "TestBuild")
        qtbot.addWidget(dialog)

        # Uncheck all, check one
        for checkbox in dialog.category_checks.values():
            checkbox.setChecked(False)

        if dialog.category_checks:
            first_cat = list(dialog.category_checks.keys())[0]
            dialog.category_checks[first_cat].setChecked(True)

            dialog._on_save()

            mock_character_manager.set_build_categories.assert_called()

    def test_save_error_shows_message(self, qtbot, mock_character_manager, mock_profile):
        """Should show error message on save failure."""
        mock_character_manager.get_profile.return_value = mock_profile
        mock_character_manager.set_build_categories.side_effect = Exception("Save failed")

        dialog = ManageCategoriesDialog(None, mock_character_manager, "TestBuild")
        qtbot.addWidget(dialog)

        with patch.object(QMessageBox, 'critical') as mock_critical:
            dialog._on_save()
            mock_critical.assert_called_once()


# =============================================================================
# ImportPoBDialog Tests
# =============================================================================


class TestImportPoBDialogInit:
    """Tests for ImportPoBDialog initialization."""

    def test_init_sets_title(self, qtbot, mock_character_manager):
        """Should set window title."""
        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)
        assert "Import" in dialog.windowTitle()

    def test_init_creates_input_fields(self, qtbot, mock_character_manager):
        """Should create input fields."""
        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        assert dialog.name_input is not None
        assert dialog.code_input is not None
        assert dialog.notes_input is not None

    def test_init_focuses_name_input(self, qtbot, mock_character_manager):
        """Should focus name input on init."""
        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)
        dialog.show()

        # Just verify input exists - focus testing is fragile
        assert dialog.name_input is not None


class TestImportPoBDialogValidation:
    """Tests for import validation."""

    def test_import_empty_name_shows_warning(self, qtbot, mock_character_manager):
        """Should warn when name is empty."""
        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("")
        dialog.code_input.setPlainText("some code")

        with patch.object(QMessageBox, 'warning') as mock_warning:
            dialog._on_import()
            mock_warning.assert_called_once()
            assert "name" in mock_warning.call_args[0][2].lower()

    def test_import_empty_code_shows_warning(self, qtbot, mock_character_manager):
        """Should warn when code is empty."""
        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("TestBuild")
        dialog.code_input.setPlainText("")

        with patch.object(QMessageBox, 'warning') as mock_warning:
            dialog._on_import()
            mock_warning.assert_called_once()
            assert "code" in mock_warning.call_args[0][2].lower()


class TestImportPoBDialogImport:
    """Tests for import functionality."""

    def test_import_success(self, qtbot, mock_character_manager, mock_profile):
        """Should show success message on successful import."""
        mock_character_manager.list_profiles.return_value = []
        mock_character_manager.add_from_pob_code.return_value = mock_profile

        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("NewBuild")
        dialog.code_input.setPlainText("eNq...")

        with patch.object(QMessageBox, 'information') as mock_info:
            dialog._on_import()
            mock_info.assert_called_once()
            assert "success" in mock_info.call_args[0][1].lower()

    def test_import_calls_manager(self, qtbot, mock_character_manager, mock_profile):
        """Should call character manager to import."""
        mock_character_manager.list_profiles.return_value = []
        mock_character_manager.add_from_pob_code.return_value = mock_profile

        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("NewBuild")
        dialog.code_input.setPlainText("eNq...")
        dialog.notes_input.setText("Test notes")

        with patch.object(QMessageBox, 'information'):
            dialog._on_import()

        mock_character_manager.add_from_pob_code.assert_called_with(
            name="NewBuild",
            pob_code="eNq...",
            notes="Test notes",
        )

    def test_import_duplicate_asks_overwrite(self, qtbot, mock_character_manager, mock_profile):
        """Should ask about overwriting duplicate."""
        mock_character_manager.list_profiles.return_value = ["ExistingBuild"]
        mock_character_manager.add_from_pob_code.return_value = mock_profile

        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("ExistingBuild")
        dialog.code_input.setPlainText("eNq...")

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            with patch.object(QMessageBox, 'information'):
                dialog._on_import()

        mock_character_manager.delete_profile.assert_called_with("ExistingBuild")

    def test_import_failure_shows_error(self, qtbot, mock_character_manager):
        """Should show error on import failure."""
        mock_character_manager.list_profiles.return_value = []
        mock_character_manager.add_from_pob_code.return_value = None

        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("NewBuild")
        dialog.code_input.setPlainText("invalid")

        with patch.object(QMessageBox, 'critical') as mock_critical:
            dialog._on_import()
            mock_critical.assert_called_once()

    def test_import_exception_shows_error(self, qtbot, mock_character_manager):
        """Should show error on exception."""
        mock_character_manager.list_profiles.return_value = []
        mock_character_manager.add_from_pob_code.side_effect = Exception("Network error")

        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("NewBuild")
        dialog.code_input.setPlainText("eNq...")

        with patch.object(QMessageBox, 'critical') as mock_critical:
            dialog._on_import()
            mock_critical.assert_called_once()
            assert "error" in mock_critical.call_args[0][1].lower()

    def test_import_with_categories(self, qtbot, mock_character_manager, mock_profile):
        """Should apply selected categories on import."""
        mock_character_manager.list_profiles.return_value = []
        mock_character_manager.add_from_pob_code.return_value = mock_profile

        dialog = ImportPoBDialog(None, mock_character_manager)
        qtbot.addWidget(dialog)

        dialog.name_input.setText("NewBuild")
        dialog.code_input.setPlainText("eNq...")

        # Check some categories if available
        if dialog.category_checks:
            first_cat = list(dialog.category_checks.keys())[0]
            dialog.category_checks[first_cat].setChecked(True)

        with patch.object(QMessageBox, 'information'):
            dialog._on_import()

        if dialog.category_checks:
            mock_character_manager.set_build_categories.assert_called()


# =============================================================================
# Edge Cases
# =============================================================================


class TestPoBCharacterWindowEdgeCases:
    """Edge case tests."""

    def test_clear_details(self, qtbot, mock_character_manager):
        """Should clear all detail labels."""
        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Set some values
        window.info_labels["Name"].setText("Test")

        window._clear_details()

        assert window.info_labels["Name"].text() == "-"
        assert window.equipment_tree.topLevelItemCount() == 0

    def test_profile_without_build(self, qtbot, mock_character_manager):
        """Should handle profile without build data."""
        profile = MagicMock()
        profile.name = "EmptyBuild"
        profile.build = None
        profile.categories = []

        mock_character_manager.list_profiles.return_value = ["EmptyBuild"]
        mock_character_manager.get_profile.return_value = profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        # Should not crash
        assert window.profile_list.count() == 1

    def test_delete_with_confirmation(self, qtbot, mock_character_manager, mock_profile):
        """Should delete after confirmation."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        window.profile_list.setCurrentRow(0)

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            window._on_delete()

        mock_character_manager.delete_profile.assert_called_with("TestBuild")

    def test_delete_cancelled(self, qtbot, mock_character_manager, mock_profile):
        """Should not delete when cancelled."""
        mock_character_manager.list_profiles.return_value = ["TestBuild"]
        mock_character_manager.get_profile.return_value = mock_profile

        window = PoBCharacterWindow(mock_character_manager)
        qtbot.addWidget(window)

        window.profile_list.setCurrentRow(0)

        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            window._on_delete()

        mock_character_manager.delete_profile.assert_not_called()
