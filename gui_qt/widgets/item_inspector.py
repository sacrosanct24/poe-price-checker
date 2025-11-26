"""
gui_qt.widgets.item_inspector

PyQt6 widget for displaying parsed item details.
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
)

from gui_qt.styles import COLORS, get_rarity_color


class ItemInspectorWidget(QWidget):
    """Widget for displaying parsed item information."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Content widget
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(4)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self._content)
        layout.addWidget(scroll)

        # Placeholder
        self._placeholder = QLabel("No item selected")
        self._placeholder.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._content_layout.addWidget(self._placeholder)

    def set_item(self, item: Any) -> None:
        """Display parsed item information."""
        self._clear_content()

        if item is None:
            self._placeholder = QLabel("No item selected")
            self._placeholder.setStyleSheet(f"color: {COLORS['text_secondary']};")
            self._content_layout.addWidget(self._placeholder)
            return

        # Item name with rarity color
        name = getattr(item, "name", "") or getattr(item, "base_type", "Unknown Item")
        rarity = getattr(item, "rarity", "Normal")

        name_label = QLabel(name)
        name_label.setWordWrap(True)
        name_font = QFont()
        name_font.setPointSize(12)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {get_rarity_color(rarity)};")
        self._content_layout.addWidget(name_label)

        # Base type (if different from name)
        base_type = getattr(item, "base_type", "")
        if base_type and base_type != name:
            base_label = QLabel(base_type)
            base_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            self._content_layout.addWidget(base_label)

        # Rarity
        rarity_label = QLabel(f"Rarity: {rarity}")
        rarity_label.setStyleSheet(f"color: {get_rarity_color(rarity)};")
        self._content_layout.addWidget(rarity_label)

        # Add separator
        self._add_separator()

        # Item level
        ilvl = getattr(item, "item_level", None) or getattr(item, "ilvl", None)
        if ilvl:
            self._add_info_row("Item Level", str(ilvl))

        # Requirements
        req_level = getattr(item, "required_level", None)
        if req_level:
            self._add_info_row("Required Level", str(req_level))

        # Sockets/links
        sockets = getattr(item, "sockets", None)
        if sockets:
            self._add_info_row("Sockets", sockets)

        links = getattr(item, "links", None) or getattr(item, "max_links", None)
        if links:
            self._add_info_row("Links", str(links))

        # Quality
        quality = getattr(item, "quality", None)
        if quality:
            self._add_info_row("Quality", f"+{quality}%")

        # Stack size
        stack = getattr(item, "stack_size", None)
        if stack:
            self._add_info_row("Stack Size", str(stack))

        # Map info
        map_tier = getattr(item, "map_tier", None)
        if map_tier:
            self._add_info_row("Map Tier", str(map_tier))

        # Gem info
        gem_level = getattr(item, "gem_level", None)
        if gem_level:
            self._add_info_row("Gem Level", str(gem_level))

        # Corrupted status
        corrupted = getattr(item, "corrupted", False)
        if corrupted:
            corrupted_label = QLabel("Corrupted")
            corrupted_label.setStyleSheet(f"color: {COLORS['corrupted']}; font-weight: bold;")
            self._content_layout.addWidget(corrupted_label)

        # Implicit mods
        implicit_mods = getattr(item, "implicit_mods", [])
        if implicit_mods:
            self._add_separator()
            for mod in implicit_mods:
                mod_label = QLabel(mod)
                mod_label.setWordWrap(True)
                mod_label.setStyleSheet(f"color: {COLORS['magic']};")
                self._content_layout.addWidget(mod_label)

        # Explicit mods
        explicit_mods = getattr(item, "explicit_mods", []) or getattr(item, "mods", [])
        if explicit_mods:
            self._add_separator()
            for mod in explicit_mods:
                mod_label = QLabel(mod)
                mod_label.setWordWrap(True)

                # Check for crafted mods
                if "(crafted)" in mod.lower():
                    mod_label.setStyleSheet("color: #b4b4ff;")
                else:
                    mod_label.setStyleSheet(f"color: {COLORS['text']};")

                self._content_layout.addWidget(mod_label)

        # Flavor text
        flavor = getattr(item, "flavor_text", None)
        if flavor:
            self._add_separator()
            flavor_label = QLabel(flavor)
            flavor_label.setWordWrap(True)
            flavor_label.setStyleSheet(f"color: {COLORS['unique']}; font-style: italic;")
            self._content_layout.addWidget(flavor_label)

        # Add stretch at end
        self._content_layout.addStretch()

    def clear(self) -> None:
        """Clear the inspector."""
        self._clear_content()
        self._placeholder = QLabel("No item selected")
        self._placeholder.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._content_layout.addWidget(self._placeholder)

    def _clear_content(self) -> None:
        """Clear all content from the layout."""
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _add_separator(self) -> None:
        """Add a horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']};")
        self._content_layout.addWidget(line)

    def _add_info_row(self, label: str, value: str) -> None:
        """Add a label: value row."""
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(f"{label}:")
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']};")
        row.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet(f"color: {COLORS['text']};")
        row.addWidget(val)

        row.addStretch()
        self._content_layout.addLayout(row)
