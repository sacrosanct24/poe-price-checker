"""
gui_qt.windows.rare_eval_config_window

PyQt6 window for configuring rare item evaluation settings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QSlider,
    QSpinBox,
    QPushButton,
    QComboBox,
    QScrollArea,
    QFormLayout,
    QMessageBox,
    QFrame,
)

from gui_qt.styles import COLORS


# Preset configurations
PRESETS = {
    "Life/Res Build": {
        "life": 10,
        "elemental_resistances": 10,
        "chaos_resistance": 6,
        "attributes": 4,
        "armor": 3,
        "evasion": 3,
        "energy_shield": 2,
        "physical_damage": 2,
        "elemental_damage": 2,
        "critical_strike": 2,
        "attack_speed": 2,
        "cast_speed": 1,
        "spell_damage": 1,
    },
    "ES Caster": {
        "energy_shield": 10,
        "spell_damage": 9,
        "cast_speed": 8,
        "critical_strike": 7,
        "elemental_damage": 7,
        "mana": 5,
        "elemental_resistances": 5,
        "chaos_resistance": 4,
        "life": 3,
        "attributes": 4,
    },
    "Physical DPS": {
        "physical_damage": 10,
        "attack_speed": 9,
        "critical_strike": 8,
        "accuracy": 7,
        "life": 7,
        "elemental_resistances": 5,
        "attributes": 5,
        "armor": 4,
        "evasion": 3,
    },
    "Elemental DPS": {
        "elemental_damage": 10,
        "attack_speed": 9,
        "critical_strike": 8,
        "life": 7,
        "elemental_resistances": 6,
        "attributes": 4,
        "accuracy": 5,
    },
    "Balanced": {
        "life": 8,
        "elemental_resistances": 7,
        "physical_damage": 5,
        "elemental_damage": 5,
        "critical_strike": 5,
        "attack_speed": 5,
        "cast_speed": 5,
        "spell_damage": 5,
        "energy_shield": 4,
        "armor": 4,
        "evasion": 4,
        "attributes": 4,
        "chaos_resistance": 4,
        "mana": 3,
        "accuracy": 3,
    },
}

# All affix types
AFFIX_TYPES = [
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


class RareEvalConfigWindow(QDialog):
    """Window for configuring rare item evaluation."""

    def __init__(
        self,
        data_dir: Path,
        parent: Optional[QWidget] = None,
        on_save: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)

        self.data_dir = data_dir
        self.on_save = on_save
        self.config_path = data_dir / "rare_eval_config.json"

        self.setWindowTitle("Rare Item Evaluation Settings")
        self.setMinimumSize(400, 450)
        self.resize(550, 650)

        self._sliders: Dict[str, QSlider] = {}
        self._spin_boxes: Dict[str, QSpinBox] = {}

        self._create_widgets()
        self._load_config()

    def _create_widgets(self) -> None:
        """Create all UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Preset selector
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- Select Preset --")
        for preset_name in PRESETS.keys():
            self.preset_combo.addItem(preset_name)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        preset_row.addWidget(self.preset_combo)

        preset_row.addStretch()
        layout.addLayout(preset_row)

        # Scrollable area for affix weights
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)

        # Affix weights group
        weights_group = QGroupBox("Affix Weights")
        weights_layout = QVBoxLayout(weights_group)

        help_label = QLabel(
            "Adjust the weight (1-10) for each affix type.\n"
            "Higher weights mean the affix contributes more to the item's score."
        )
        help_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        help_label.setWordWrap(True)
        weights_layout.addWidget(help_label)

        for affix in AFFIX_TYPES:
            row = QHBoxLayout()

            # Label
            label = QLabel(affix.replace("_", " ").title() + ":")
            label.setMinimumWidth(150)
            row.addWidget(label)

            # Slider
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(1, 10)
            slider.setValue(5)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setTickInterval(1)
            slider.valueChanged.connect(lambda v, a=affix: self._on_slider_changed(a, v))
            self._sliders[affix] = slider
            row.addWidget(slider)

            # Spin box
            spin = QSpinBox()
            spin.setRange(1, 10)
            spin.setValue(5)
            spin.setMinimumWidth(50)
            spin.valueChanged.connect(lambda v, a=affix: self._on_spin_changed(a, v))
            self._spin_boxes[affix] = spin
            row.addWidget(spin)

            weights_layout.addLayout(row)

        content_layout.addWidget(weights_group)

        # Threshold settings
        threshold_group = QGroupBox("Thresholds")
        threshold_layout = QFormLayout(threshold_group)

        self.min_tier_spin = QSpinBox()
        self.min_tier_spin.setRange(1, 5)
        self.min_tier_spin.setValue(3)
        threshold_layout.addRow("Minimum Tier to Count:", self.min_tier_spin)

        self.excellent_threshold_spin = QSpinBox()
        self.excellent_threshold_spin.setRange(50, 100)
        self.excellent_threshold_spin.setValue(80)
        threshold_layout.addRow("Excellent Threshold:", self.excellent_threshold_spin)

        self.good_threshold_spin = QSpinBox()
        self.good_threshold_spin.setRange(30, 80)
        self.good_threshold_spin.setValue(60)
        threshold_layout.addRow("Good Threshold:", self.good_threshold_spin)

        self.average_threshold_spin = QSpinBox()
        self.average_threshold_spin.setRange(10, 60)
        self.average_threshold_spin.setValue(40)
        threshold_layout.addRow("Average Threshold:", self.average_threshold_spin)

        content_layout.addWidget(threshold_group)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _on_slider_changed(self, affix: str, value: int) -> None:
        """Handle slider value change."""
        self._spin_boxes[affix].blockSignals(True)
        self._spin_boxes[affix].setValue(value)
        self._spin_boxes[affix].blockSignals(False)

    def _on_spin_changed(self, affix: str, value: int) -> None:
        """Handle spin box value change."""
        self._sliders[affix].blockSignals(True)
        self._sliders[affix].setValue(value)
        self._sliders[affix].blockSignals(False)

    def _on_preset_selected(self, preset_name: str) -> None:
        """Apply a preset configuration."""
        if preset_name == "-- Select Preset --":
            return

        preset = PRESETS.get(preset_name)
        if not preset:
            return

        for affix in AFFIX_TYPES:
            value = preset.get(affix, 5)
            self._sliders[affix].setValue(value)
            self._spin_boxes[affix].setValue(value)

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            return

        try:
            config = json.loads(self.config_path.read_text(encoding="utf-8"))

            # Load weights
            weights = config.get("weights", {})
            for affix, value in weights.items():
                if affix in self._sliders:
                    self._sliders[affix].setValue(value)
                    self._spin_boxes[affix].setValue(value)

            # Load thresholds
            thresholds = config.get("thresholds", {})
            if "min_tier" in thresholds:
                self.min_tier_spin.setValue(thresholds["min_tier"])
            if "excellent" in thresholds:
                self.excellent_threshold_spin.setValue(thresholds["excellent"])
            if "good" in thresholds:
                self.good_threshold_spin.setValue(thresholds["good"])
            if "average" in thresholds:
                self.average_threshold_spin.setValue(thresholds["average"])

        except Exception as e:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Failed to load configuration:\n{e}",
            )

    def _reset_defaults(self) -> None:
        """Reset all values to defaults."""
        for affix in AFFIX_TYPES:
            self._sliders[affix].setValue(5)
            self._spin_boxes[affix].setValue(5)

        self.min_tier_spin.setValue(3)
        self.excellent_threshold_spin.setValue(80)
        self.good_threshold_spin.setValue(60)
        self.average_threshold_spin.setValue(40)

        self.preset_combo.setCurrentIndex(0)

    def _on_save(self) -> None:
        """Save configuration."""
        config = {
            "weights": {
                affix: self._sliders[affix].value()
                for affix in AFFIX_TYPES
            },
            "thresholds": {
                "min_tier": self.min_tier_spin.value(),
                "excellent": self.excellent_threshold_spin.value(),
                "good": self.good_threshold_spin.value(),
                "average": self.average_threshold_spin.value(),
            },
        }

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(config, indent=2),
                encoding="utf-8",
            )

            if self.on_save:
                self.on_save()

            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save configuration:\n{e}",
            )
