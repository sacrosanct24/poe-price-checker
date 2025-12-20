"""Tests for ClearBuildsDialog."""

from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QWidget, QMessageBox


class TestClearBuildsDialogInit:
    """Tests for ClearBuildsDialog initialization."""

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_init_with_defaults(self, qtbot):
        """Can initialize with default parameters."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Clear Builds"
        assert dialog.character_manager is None

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_init_with_parent(self, qtbot):
        """Can initialize with parent."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        parent = QWidget()
        qtbot.addWidget(parent)

        dialog = ClearBuildsDialog(parent=parent)
        qtbot.addWidget(dialog)

        assert dialog.parent() == parent

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_init_with_character_manager(self, qtbot):
        """Can initialize with character manager."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        mock_manager = MagicMock()
        mock_manager.list_profiles.return_value = []

        dialog = ClearBuildsDialog(character_manager=mock_manager)
        qtbot.addWidget(dialog)

        assert dialog.character_manager is mock_manager

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_has_minimum_width(self, qtbot):
        """Dialog has minimum width of 400."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() == 400

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    @patch("gui_qt.dialogs.clear_builds_dialog.apply_window_icon")
    def test_applies_window_icon(self, mock_apply_icon, qtbot):
        """Dialog applies window icon."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        mock_apply_icon.assert_called_once_with(dialog)

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_initializes_category_checkboxes(self, qtbot):
        """Initializes category checkboxes dictionary."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "_category_checkboxes")
        assert isinstance(dialog._category_checkboxes, dict)

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_initializes_profiles_to_delete_list(self, qtbot):
        """Initializes profiles to delete list."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "_profiles_to_delete")
        assert isinstance(dialog._profiles_to_delete, list)


class TestClearBuildsDialogWidgets:
    """Tests for ClearBuildsDialog widget creation."""

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_has_warning_label(self, qtbot):
        """Dialog has warning label."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        # Widget is created during initialization

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_has_protect_active_checkbox(self, qtbot):
        """Dialog has protect active checkbox."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "protect_active")
        assert dialog.protect_active is not None

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_protect_active_checked_by_default(self, qtbot):
        """Protect active checkbox is checked by default."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert dialog.protect_active.isChecked() is True

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_has_protect_upgrade_target_checkbox(self, qtbot):
        """Dialog has protect upgrade target checkbox."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "protect_upgrade_target")
        assert dialog.protect_upgrade_target is not None

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_protect_upgrade_target_checked_by_default(self, qtbot):
        """Protect upgrade target checkbox is checked by default."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert dialog.protect_upgrade_target.isChecked() is True

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_has_preview_label(self, qtbot):
        """Dialog has preview label."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "preview_label")
        assert dialog.preview_label is not None

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_has_delete_button(self, qtbot):
        """Dialog has delete button."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "delete_btn")
        assert dialog.delete_btn is not None


class TestClearBuildsDialogCategoryCheckboxes:
    """Tests for category checkbox creation."""

    def test_creates_checkbox_for_each_category(self, qtbot):
        """Creates a checkbox for each build category."""
        # Mock BuildCategory enum
        mock_cat1 = MagicMock()
        mock_cat1.value = "my_builds"
        mock_cat2 = MagicMock()
        mock_cat2.value = "reference"
        mock_cat3 = MagicMock()
        mock_cat3.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat1, mock_cat2, mock_cat3]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = []

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            assert len(dialog._category_checkboxes) == 3
            assert "my_builds" in dialog._category_checkboxes
            assert "reference" in dialog._category_checkboxes
            assert "testing" in dialog._category_checkboxes

    def test_protected_categories_checked_by_default(self, qtbot):
        """Protected categories are checked by default."""
        mock_cat1 = MagicMock()
        mock_cat1.value = "my_builds"
        mock_cat2 = MagicMock()
        mock_cat2.value = "reference"
        mock_cat3 = MagicMock()
        mock_cat3.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat1, mock_cat2, mock_cat3]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = []

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            # my_builds and reference are protected by default
            assert dialog._category_checkboxes["my_builds"].isChecked() is True
            assert dialog._category_checkboxes["reference"].isChecked() is True
            assert dialog._category_checkboxes["testing"].isChecked() is False


class TestClearBuildsDialogUpdatePreview:
    """Tests for preview update logic."""

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_preview_with_no_character_manager(self, qtbot):
        """Preview handles missing character manager."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        dialog._update_preview()

        assert dialog.delete_btn.isEnabled() is False
        assert "No character manager" in dialog.preview_label.text()

    def test_preview_shows_delete_count(self, qtbot):
        """Preview shows count of builds to delete."""
        mock_cat = MagicMock()
        mock_cat.value = "my_builds"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["build1", "build2"]

            # Mock get_profile to return profiles without protected categories
            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            # Uncheck protect_active to allow deletion
            dialog.protect_active.setChecked(False)
            dialog._update_preview()

            assert len(dialog._profiles_to_delete) == 2

    def test_preview_protects_active_profile(self, qtbot):
        """Preview protects active profile when checkbox checked."""
        mock_cat = MagicMock()
        mock_cat.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["active_build", "other_build"]

            # Set up active profile
            mock_active = MagicMock()
            mock_active.name = "active_build"
            mock_active.categories = []
            mock_manager.get_active_profile.return_value = mock_active
            mock_manager.get_upgrade_target.return_value = None

            # Set up profiles
            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            # active_build should be protected
            assert "active_build" not in dialog._profiles_to_delete
            assert "other_build" in dialog._profiles_to_delete

    def test_preview_protects_upgrade_target(self, qtbot):
        """Preview protects upgrade target when checkbox checked."""
        mock_cat = MagicMock()
        mock_cat.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["upgrade_build", "other_build"]

            # Set up upgrade target
            mock_upgrade = MagicMock()
            mock_upgrade.name = "upgrade_build"
            mock_upgrade.categories = []
            mock_manager.get_upgrade_target.return_value = mock_upgrade
            mock_manager.get_active_profile.return_value = None

            # Set up profiles
            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            # upgrade_build should be protected
            assert "upgrade_build" not in dialog._profiles_to_delete
            assert "other_build" in dialog._profiles_to_delete

    def test_preview_protects_by_category(self, qtbot):
        """Preview protects builds with checked categories."""
        mock_cat1 = MagicMock()
        mock_cat1.value = "my_builds"
        mock_cat2 = MagicMock()
        mock_cat2.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat1, mock_cat2]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["build_with_cat", "build_without_cat"]
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            # First profile has protected category
            mock_profile1 = MagicMock()
            mock_profile1.categories = ["my_builds"]

            # Second profile has no protected category
            mock_profile2 = MagicMock()
            mock_profile2.categories = ["testing"]

            def get_profile_side_effect(name):
                if name == "build_with_cat":
                    return mock_profile1
                return mock_profile2

            mock_manager.get_profile.side_effect = get_profile_side_effect

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            # build_with_cat has protected category (my_builds is checked by default)
            assert "build_with_cat" not in dialog._profiles_to_delete
            # build_without_cat only has testing category (not protected by default)
            assert "build_without_cat" in dialog._profiles_to_delete

    def test_preview_disables_button_when_no_deletions(self, qtbot):
        """Delete button is disabled when no builds to delete."""
        mock_cat = MagicMock()
        mock_cat.value = "my_builds"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["protected_build"]
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            # Profile has protected category
            mock_profile = MagicMock()
            mock_profile.categories = ["my_builds"]
            mock_manager.get_profile.return_value = mock_profile

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            assert len(dialog._profiles_to_delete) == 0
            assert dialog.delete_btn.isEnabled() is False

    def test_preview_enables_button_when_deletions_available(self, qtbot):
        """Delete button is enabled when builds can be deleted."""
        mock_cat = MagicMock()
        mock_cat.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["deletable_build"]
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            # Profile has no protected category
            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            assert len(dialog._profiles_to_delete) == 1
            assert dialog.delete_btn.isEnabled() is True


class TestClearBuildsDialogDeleteAction:
    """Tests for delete action."""

    def test_delete_requires_confirmation(self, qtbot):
        """Delete action requires user confirmation."""
        mock_cat = MagicMock()
        mock_cat.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["build1"]
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            # Mock QMessageBox.warning to return No
            with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.No):
                dialog._on_delete()

                # Should not delete if user says No
                mock_manager.delete_profile.assert_not_called()

    def test_delete_executes_when_confirmed(self, qtbot):
        """Delete executes when user confirms."""
        mock_cat = MagicMock()
        mock_cat.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["build1", "build2"]
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            # Mock QMessageBox.warning to return Yes
            with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Yes):
                with patch.object(dialog, "accept"):
                    dialog._on_delete()

                    # Should delete both builds
                    assert mock_manager.delete_profile.call_count == 2

    def test_delete_handles_errors_gracefully(self, qtbot):
        """Delete handles errors without crashing."""
        mock_cat = MagicMock()
        mock_cat.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["build1", "build2"]
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile

            # Make delete_profile raise an error for first build
            mock_manager.delete_profile.side_effect = [Exception("Test error"), None]

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Yes):
                with patch.object(dialog, "accept"):
                    # Should not crash
                    dialog._on_delete()

                    # Should attempt both deletions
                    assert mock_manager.delete_profile.call_count == 2

    def test_delete_does_nothing_when_no_profiles(self, qtbot):
        """Delete does nothing when no profiles to delete."""
        mock_cat = MagicMock()
        mock_cat.value = "my_builds"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = []
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._on_delete()

            # Should not show confirmation or delete
            mock_manager.delete_profile.assert_not_called()


class TestClearBuildsDialogGetDeletedCount:
    """Tests for get_deleted_count method."""

    @patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [])
    def test_get_deleted_count_returns_zero_initially(self, qtbot):
        """get_deleted_count returns 0 initially."""
        from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

        dialog = ClearBuildsDialog()
        qtbot.addWidget(dialog)

        assert dialog.get_deleted_count() == 0

    def test_get_deleted_count_returns_profiles_count(self, qtbot):
        """get_deleted_count returns count of profiles to delete."""
        mock_cat = MagicMock()
        mock_cat.value = "testing"

        with patch("gui_qt.dialogs.clear_builds_dialog.BUILD_CATEGORIES", [mock_cat]):
            from gui_qt.dialogs.clear_builds_dialog import ClearBuildsDialog

            mock_manager = MagicMock()
            mock_manager.list_profiles.return_value = ["build1", "build2", "build3"]
            mock_manager.get_active_profile.return_value = None
            mock_manager.get_upgrade_target.return_value = None

            mock_profile = MagicMock()
            mock_profile.categories = []
            mock_manager.get_profile.return_value = mock_profile

            dialog = ClearBuildsDialog(character_manager=mock_manager)
            qtbot.addWidget(dialog)

            dialog._update_preview()

            assert dialog.get_deleted_count() == 3
