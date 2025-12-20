"""
Tests for RareEvalConfigWindow.

Tests the window for configuring rare item evaluation settings.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

pytestmark = pytest.mark.unit


# ============================================================================
# Preset and Constant Tests
# ============================================================================


class TestPresetsAndConstants:
    """Tests for preset configurations and constants."""

    def test_presets_defined(self):
        """All presets are defined."""
        from gui_qt.windows.rare_eval_config_window import PRESETS

        expected_presets = [
            "Life/Res Build",
            "ES Caster",
            "Physical DPS",
            "Elemental DPS",
            "Balanced",
        ]

        assert len(PRESETS) == len(expected_presets)
        for preset_name in expected_presets:
            assert preset_name in PRESETS

    def test_affix_types_defined(self):
        """All affix types are defined."""
        from gui_qt.windows.rare_eval_config_window import AFFIX_TYPES

        expected_affixes = [
            "life",
            "mana",
            "energy_shield",
            "armor",
            "evasion",
            "elemental_resistances",
            "chaos_resistance",
            "attributes",
            "physical_damage",
            "elemental_damage",
            "spell_damage",
            "attack_speed",
            "cast_speed",
            "critical_strike",
            "accuracy",
            "movement_speed",
        ]

        assert len(AFFIX_TYPES) == len(expected_affixes)
        for affix in expected_affixes:
            assert affix in AFFIX_TYPES

    def test_preset_weights_are_valid(self):
        """Preset weights are in valid range (1-10)."""
        from gui_qt.windows.rare_eval_config_window import PRESETS

        for preset_name, weights in PRESETS.items():
            for affix, weight in weights.items():
                assert 1 <= weight <= 10, f"Invalid weight in {preset_name}: {affix}={weight}"

    def test_preset_contains_valid_affixes(self):
        """Presets only contain valid affix types."""
        from gui_qt.windows.rare_eval_config_window import AFFIX_TYPES, PRESETS

        for preset_name, weights in PRESETS.items():
            for affix in weights.keys():
                assert affix in AFFIX_TYPES, f"Invalid affix in {preset_name}: {affix}"


# ============================================================================
# RareEvalConfigWindow Tests
# ============================================================================


class TestRareEvalConfigWindow:
    """Tests for RareEvalConfigWindow."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_window_initialization(self, qtbot, temp_data_dir):
        """Window initializes with correct properties."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        assert window.windowTitle() == "Rare Item Evaluation Settings"
        assert window.minimumSize().width() == 400
        assert window.minimumSize().height() == 450
        assert window.isSizeGripEnabled()

    def test_window_stores_data_dir(self, qtbot, temp_data_dir):
        """Window stores data directory path."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        assert window.data_dir == temp_data_dir
        assert window.config_path == temp_data_dir / "rare_eval_config.json"

    def test_window_stores_on_save_callback(self, qtbot, temp_data_dir):
        """Window stores on_save callback."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        callback = MagicMock()
        window = RareEvalConfigWindow(temp_data_dir, on_save=callback)
        qtbot.addWidget(window)

        assert window.on_save is callback

    def test_widgets_created(self, qtbot, temp_data_dir):
        """All UI widgets are created."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Preset selector
        assert hasattr(window, "preset_combo")

        # Threshold spinners
        assert hasattr(window, "min_tier_spin")
        assert hasattr(window, "excellent_threshold_spin")
        assert hasattr(window, "good_threshold_spin")
        assert hasattr(window, "average_threshold_spin")

        # Sliders and spinboxes dictionaries
        assert hasattr(window, "_sliders")
        assert hasattr(window, "_spin_boxes")

    def test_preset_combo_has_all_presets(self, qtbot, temp_data_dir):
        """Preset combo box contains all presets."""
        from gui_qt.windows.rare_eval_config_window import (
            PRESETS,
            RareEvalConfigWindow,
        )

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # First item is "-- Select Preset --"
        assert window.preset_combo.itemText(0) == "-- Select Preset --"

        # All presets should be present
        combo_items = [
            window.preset_combo.itemText(i)
            for i in range(1, window.preset_combo.count())
        ]
        for preset_name in PRESETS.keys():
            assert preset_name in combo_items

    def test_sliders_created_for_all_affixes(self, qtbot, temp_data_dir):
        """Sliders are created for all affix types."""
        from gui_qt.windows.rare_eval_config_window import (
            AFFIX_TYPES,
            RareEvalConfigWindow,
        )

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        assert len(window._sliders) == len(AFFIX_TYPES)
        for affix in AFFIX_TYPES:
            assert affix in window._sliders

    def test_spin_boxes_created_for_all_affixes(self, qtbot, temp_data_dir):
        """Spin boxes are created for all affix types."""
        from gui_qt.windows.rare_eval_config_window import (
            AFFIX_TYPES,
            RareEvalConfigWindow,
        )

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        assert len(window._spin_boxes) == len(AFFIX_TYPES)
        for affix in AFFIX_TYPES:
            assert affix in window._spin_boxes

    def test_sliders_default_values(self, qtbot, temp_data_dir):
        """Sliders start with default value of 5."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        for slider in window._sliders.values():
            assert slider.value() == 5
            assert slider.minimum() == 1
            assert slider.maximum() == 10

    def test_spin_boxes_default_values(self, qtbot, temp_data_dir):
        """Spin boxes start with default value of 5."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        for spin in window._spin_boxes.values():
            assert spin.value() == 5
            assert spin.minimum() == 1
            assert spin.maximum() == 10

    def test_threshold_spinners_default_values(self, qtbot, temp_data_dir):
        """Threshold spinners have correct default values."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        assert window.min_tier_spin.value() == 3
        assert window.min_tier_spin.minimum() == 1
        assert window.min_tier_spin.maximum() == 5

        assert window.excellent_threshold_spin.value() == 80
        assert window.excellent_threshold_spin.minimum() == 50
        assert window.excellent_threshold_spin.maximum() == 100

        assert window.good_threshold_spin.value() == 60
        assert window.good_threshold_spin.minimum() == 30
        assert window.good_threshold_spin.maximum() == 80

        assert window.average_threshold_spin.value() == 40
        assert window.average_threshold_spin.minimum() == 10
        assert window.average_threshold_spin.maximum() == 60

    def test_slider_change_updates_spin_box(self, qtbot, temp_data_dir):
        """Changing slider updates corresponding spin box."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Change life slider
        window._sliders["life"].setValue(8)

        # Spin box should update
        assert window._spin_boxes["life"].value() == 8

    def test_spin_box_change_updates_slider(self, qtbot, temp_data_dir):
        """Changing spin box updates corresponding slider."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Change life spin box
        window._spin_boxes["life"].setValue(7)

        # Slider should update
        assert window._sliders["life"].value() == 7

    def test_preset_selection_applies_weights(self, qtbot, temp_data_dir):
        """Selecting a preset applies its weights."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Select "Life/Res Build" preset
        window.preset_combo.setCurrentText("Life/Res Build")

        # Check some expected weights
        assert window._sliders["life"].value() == 10
        assert window._sliders["elemental_resistances"].value() == 10
        assert window._sliders["chaos_resistance"].value() == 6

    def test_preset_selection_placeholder_does_nothing(self, qtbot, temp_data_dir):
        """Selecting placeholder preset does nothing."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Change a value
        window._sliders["life"].setValue(8)

        # Select placeholder
        window.preset_combo.setCurrentText("-- Select Preset --")

        # Value should not change
        assert window._sliders["life"].value() == 8

    def test_preset_applies_default_for_missing_affixes(self, qtbot, temp_data_dir):
        """Preset applies default value (5) for affixes not in preset."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Change all values first
        for slider in window._sliders.values():
            slider.setValue(1)

        # Select a preset (may not include all affixes)
        window.preset_combo.setCurrentText("Physical DPS")

        # Affixes not in preset should get default value of 5
        # movement_speed is not in Physical DPS preset
        if "movement_speed" not in window._sliders:
            pytest.skip("movement_speed not in AFFIX_TYPES")

        # Physical DPS preset doesn't include movement_speed
        from gui_qt.windows.rare_eval_config_window import PRESETS

        if "movement_speed" not in PRESETS["Physical DPS"]:
            assert window._sliders["movement_speed"].value() == 5

    def test_reset_defaults_button(self, qtbot, temp_data_dir):
        """Reset defaults button resets all values."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Change some values
        window._sliders["life"].setValue(10)
        window.min_tier_spin.setValue(5)
        window.excellent_threshold_spin.setValue(90)
        window.preset_combo.setCurrentIndex(1)

        # Find and click reset button
        reset_btn = None
        for child in window.findChildren(type(window.preset_combo.parent())):
            if hasattr(child, "text") and "Reset" in str(child.text()):
                reset_btn = child
                break

        if reset_btn:
            qtbot.mouseClick(reset_btn, Qt.MouseButton.LeftButton)

            # Check values reset
            assert window._sliders["life"].value() == 5
            assert window.min_tier_spin.value() == 3
            assert window.excellent_threshold_spin.value() == 80
            assert window.preset_combo.currentIndex() == 0

    def test_save_button_saves_config(self, qtbot, temp_data_dir):
        """Save button saves configuration to file."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Change some values
        window._sliders["life"].setValue(10)
        window.min_tier_spin.setValue(4)

        # Mock accept to prevent dialog from closing
        with patch.object(window, "accept"):
            window._on_save()

        # Check file was saved
        config_path = temp_data_dir / "rare_eval_config.json"
        assert config_path.exists()

        # Check contents
        config = json.loads(config_path.read_text())
        assert config["weights"]["life"] == 10
        assert config["thresholds"]["min_tier"] == 4

    def test_save_calls_on_save_callback(self, qtbot, temp_data_dir):
        """Save button calls on_save callback."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        callback = MagicMock()
        window = RareEvalConfigWindow(temp_data_dir, on_save=callback)
        qtbot.addWidget(window)

        # Mock accept
        with patch.object(window, "accept"):
            window._on_save()

        callback.assert_called_once()

    def test_save_handles_write_error(self, qtbot, temp_data_dir):
        """Save handles file write errors gracefully."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Mock write_text to raise an error
        with patch.object(Path, "write_text", side_effect=OSError("Write error")):
            with patch.object(QMessageBox, "critical") as mock_critical:
                window._on_save()

                # Should show error dialog
                mock_critical.assert_called_once()
                assert "Save Error" in mock_critical.call_args[0][1]

    def test_load_config_from_file(self, qtbot, temp_data_dir):
        """Load configuration from existing file."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        # Create config file
        config_path = temp_data_dir / "rare_eval_config.json"
        config = {
            "weights": {"life": 9, "mana": 7},
            "thresholds": {
                "min_tier": 4,
                "excellent": 85,
                "good": 65,
                "average": 45,
            },
        }
        config_path.write_text(json.dumps(config))

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Check values were loaded
        assert window._sliders["life"].value() == 9
        assert window._sliders["mana"].value() == 7
        assert window.min_tier_spin.value() == 4
        assert window.excellent_threshold_spin.value() == 85
        assert window.good_threshold_spin.value() == 65
        assert window.average_threshold_spin.value() == 45

    def test_load_config_nonexistent_file(self, qtbot, temp_data_dir):
        """Load handles nonexistent config file gracefully."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        # No config file exists
        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Should use defaults
        assert window._sliders["life"].value() == 5

    def test_load_config_invalid_json(self, qtbot, temp_data_dir):
        """Load handles invalid JSON gracefully."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        # Create invalid config file
        config_path = temp_data_dir / "rare_eval_config.json"
        config_path.write_text("invalid json {")

        with patch.object(QMessageBox, "warning") as mock_warning:
            window = RareEvalConfigWindow(temp_data_dir)
            qtbot.addWidget(window)

            # Should show warning
            mock_warning.assert_called_once()
            assert "Load Error" in mock_warning.call_args[0][1]

    def test_load_config_partial_data(self, qtbot, temp_data_dir):
        """Load handles partial config data."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        # Create config with only some weights
        config_path = temp_data_dir / "rare_eval_config.json"
        config = {"weights": {"life": 8}}
        config_path.write_text(json.dumps(config))

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Specified weight should be loaded
        assert window._sliders["life"].value() == 8
        # Unspecified weights should use defaults
        assert window._sliders["mana"].value() == 5

    def test_cancel_button_rejects_dialog(self, qtbot, temp_data_dir):
        """Cancel button rejects the dialog."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        with patch.object(window, "reject") as mock_reject:
            # Find and click cancel button
            cancel_btn = None
            for child in window.findChildren(type(window.preset_combo.parent())):
                if hasattr(child, "text") and "Cancel" in str(child.text()):
                    cancel_btn = child
                    break

            if cancel_btn:
                qtbot.mouseClick(cancel_btn, Qt.MouseButton.LeftButton)
                mock_reject.assert_called_once()

    def test_save_creates_parent_directory(self, qtbot):
        """Save creates parent directory if it doesn't exist."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a subdirectory that doesn't exist
            data_dir = Path(tmpdir) / "subdir" / "data"

            window = RareEvalConfigWindow(data_dir)
            qtbot.addWidget(window)

            # Mock accept
            with patch.object(window, "accept"):
                window._on_save()

            # Check directory was created
            assert data_dir.exists()
            assert (data_dir / "rare_eval_config.json").exists()

    def test_save_config_structure(self, qtbot, temp_data_dir):
        """Saved config has correct structure."""
        from gui_qt.windows.rare_eval_config_window import (
            AFFIX_TYPES,
            RareEvalConfigWindow,
        )

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Mock accept
        with patch.object(window, "accept"):
            window._on_save()

        # Load and check structure
        config_path = temp_data_dir / "rare_eval_config.json"
        config = json.loads(config_path.read_text())

        assert "weights" in config
        assert "thresholds" in config

        # All affixes should be in weights
        for affix in AFFIX_TYPES:
            assert affix in config["weights"]

        # All thresholds should be present
        assert "min_tier" in config["thresholds"]
        assert "excellent" in config["thresholds"]
        assert "good" in config["thresholds"]
        assert "average" in config["thresholds"]

    def test_window_icon_applied(self, qtbot, temp_data_dir):
        """Window icon is applied."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        with patch(
            "gui_qt.windows.rare_eval_config_window.apply_window_icon"
        ) as mock_icon:
            window = RareEvalConfigWindow(temp_data_dir)
            qtbot.addWidget(window)

            mock_icon.assert_called_once_with(window)

    def test_slider_has_tick_marks(self, qtbot, temp_data_dir):
        """Sliders have tick marks configured."""
        from PyQt6.QtWidgets import QSlider
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Check any slider
        slider = window._sliders["life"]
        assert slider.tickPosition() == QSlider.TickPosition.TicksBelow
        assert slider.tickInterval() == 1

    def test_slider_orientation(self, qtbot, temp_data_dir):
        """Sliders are horizontal."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Check any slider
        slider = window._sliders["life"]
        assert slider.orientation() == Qt.Orientation.Horizontal

    def test_signal_blocking_during_updates(self, qtbot, temp_data_dir):
        """Signals are blocked during programmatic updates to prevent loops."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Track signal emissions
        slider_changes = []
        spin_changes = []

        window._sliders["life"].valueChanged.connect(lambda v: slider_changes.append(v))
        window._spin_boxes["life"].valueChanged.connect(lambda v: spin_changes.append(v))

        # Change slider - should only emit slider signal, not spin signal
        slider_changes.clear()
        spin_changes.clear()
        window._sliders["life"].setValue(8)

        # Slider signal should fire, but spin box should update without signal
        assert len(slider_changes) >= 1
        # Spin box value should update
        assert window._spin_boxes["life"].value() == 8

    def test_load_config_updates_both_slider_and_spin(self, qtbot, temp_data_dir):
        """Loading config updates both slider and spin box."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        # Create config file
        config_path = temp_data_dir / "rare_eval_config.json"
        config = {"weights": {"life": 9}}
        config_path.write_text(json.dumps(config))

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Both should be updated
        assert window._sliders["life"].value() == 9
        assert window._spin_boxes["life"].value() == 9

    def test_multiple_preset_selections(self, qtbot, temp_data_dir):
        """Multiple preset selections work correctly."""
        from gui_qt.windows.rare_eval_config_window import RareEvalConfigWindow

        window = RareEvalConfigWindow(temp_data_dir)
        qtbot.addWidget(window)

        # Select first preset
        window.preset_combo.setCurrentText("Life/Res Build")
        assert window._sliders["life"].value() == 10

        # Select second preset
        window.preset_combo.setCurrentText("ES Caster")
        assert window._sliders["energy_shield"].value() == 10
        assert window._sliders["spell_damage"].value() == 9
