"""
gui_qt.widgets.poe_item_tooltip

A PoE-style item tooltip widget that mimics the in-game item display.
Shows item name, base type, properties, and mods with tier information.

Triggered by Alt+hover over item names anywhere in the application.
"""

from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING, Any, Optional

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
    QApplication,
    QGraphicsDropShadowEffect,
)

from gui_qt.styles import get_rarity_color, get_tier_color
from core.mod_tier_detector import detect_mod_tier

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# PoE-style colors
POE_TOOLTIP_COLORS = {
    # Background and borders
    "background": "#0c0b0b",          # Near-black background
    "border": "#3d3326",              # Dark gold border
    "header_bg": "#1a1410",           # Slightly lighter header background
    "separator": "#3d3326",           # Gold separator line

    # Text colors
    "property_name": "#8888ff",       # Blue for property names (Item Level:, Requires:)
    "property_value": "#ffffff",      # White for property values
    "implicit_label": "#8888ff",      # Blue for "Implicit Modifier"
    "mod_value": "#8888ff",           # Blue for mod values
    "mod_info": "#7f7f7f",            # Gray for mod tier info
    "corrupted": "#d20000",           # Red for corrupted
    "mirrored": "#aa55ff",            # Purple for mirrored
    "crafted": "#b4b4ff",             # Light purple for crafted mods
    "enchant": "#b4b4ff",             # Light purple for enchants
    "fractured": "#a29162",           # Gold-ish for fractured
}


class PoEItemTooltip(QFrame):
    """
    A custom tooltip widget styled like Path of Exile's in-game item display.

    Features:
    - Header with item name and base type (colored by rarity)
    - Separator lines matching PoE style
    - Properties section (Item Level, Requirements)
    - Implicit mods section with tier info
    - Explicit mods section with prefix/suffix and tier info
    - Status indicators (Corrupted, Mirrored, etc.)
    """

    _instance: Optional["PoEItemTooltip"] = None

    @classmethod
    def instance(cls) -> "PoEItemTooltip":
        """Get or create the singleton tooltip instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Window flags for tooltip behavior
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Styling
        self.setStyleSheet(f"""
            PoEItemTooltip {{
                background-color: {POE_TOOLTIP_COLORS["background"]};
                border: 2px solid {POE_TOOLTIP_COLORS["border"]};
                border-radius: 0px;
            }}
        """)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)

        # Layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 6, 8, 6)
        self._layout.setSpacing(2)

        # Content label (we'll use HTML for rich formatting)
        self._content = QLabel()
        self._content.setTextFormat(Qt.TextFormat.RichText)
        self._content.setWordWrap(True)
        self._content.setStyleSheet("background: transparent;")
        self._layout.addWidget(self._content)

        # Hide timer
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        # Current item
        self._current_item: Optional[Any] = None

        self.setMaximumWidth(450)
        self.hide()

    def show_for_item(self, item: Any, pos: QPoint) -> None:
        """
        Show the tooltip for the given item at the specified position.

        Args:
            item: ParsedItem or similar object with item data
            pos: Global screen position to show the tooltip
        """
        if item is None:
            self.hide()
            return

        self._current_item = item
        self._hide_timer.stop()

        # Build and set content
        html_content = self._build_html(item)
        self._content.setText(html_content)

        # Adjust size to content
        self.adjustSize()

        # Position tooltip, keeping on screen
        self._position_tooltip(pos)

        self.show()
        self.raise_()

    def _position_tooltip(self, pos: QPoint) -> None:
        """Position tooltip near cursor, keeping it on screen."""
        screen = QApplication.screenAt(pos)
        if screen is None:
            screen = QApplication.primaryScreen()

        screen_rect = screen.availableGeometry()
        tooltip_size = self.sizeHint()

        # Offset from cursor
        x = pos.x() + 15
        y = pos.y() + 15

        # Keep on screen horizontally
        if x + tooltip_size.width() > screen_rect.right():
            x = pos.x() - tooltip_size.width() - 10

        # Keep on screen vertically
        if y + tooltip_size.height() > screen_rect.bottom():
            y = pos.y() - tooltip_size.height() - 10

        # Ensure not off the left/top
        x = max(screen_rect.left(), x)
        y = max(screen_rect.top(), y)

        self.move(x, y)

    def hide_after_delay(self, delay_ms: int = 100) -> None:
        """Hide the tooltip after a short delay."""
        self._hide_timer.start(delay_ms)

    def cancel_hide(self) -> None:
        """Cancel any pending hide operation."""
        self._hide_timer.stop()

    def _build_html(self, item: Any) -> str:
        """Build HTML content for the tooltip."""
        parts = []

        # Get item properties
        rarity = getattr(item, "rarity", "Normal") or "Normal"
        name = getattr(item, "name", "") or ""
        base_type = getattr(item, "base_type", "") or ""

        # Header with name and base type
        parts.append(self._build_header(name, base_type, rarity))

        # Separator after header
        parts.append(self._separator())

        # Item Level and Requirements
        props_html = self._build_properties(item)
        if props_html:
            parts.append(props_html)
            parts.append(self._separator())

        # Sockets
        sockets = getattr(item, "sockets", None)
        if sockets:
            parts.append(f'<div style="color: #ffffff; font-size: 11px;">Sockets: {html.escape(str(sockets))}</div>')

        # Implicit mods
        implicits = getattr(item, "implicits", []) or []
        if implicits:
            parts.append(self._separator())
            for mod in implicits:
                parts.append(self._build_mod_line(mod, is_implicit=True))

        # Enchants
        enchants = getattr(item, "enchants", []) or []
        if enchants:
            parts.append(self._separator())
            for mod in enchants:
                parts.append(self._build_enchant_line(mod))

        # Explicit mods
        explicits = getattr(item, "explicits", []) or []
        if explicits:
            parts.append(self._separator())
            for mod in explicits:
                parts.append(self._build_mod_line(mod, is_implicit=False))

        # Status flags
        status_html = self._build_status_flags(item)
        if status_html:
            parts.append(self._separator())
            parts.append(status_html)

        # Flavour text for uniques
        flavour = getattr(item, "flavour_text", None)
        if flavour and rarity.lower() == "unique":
            parts.append(self._separator())
            parts.append(f'<div style="color: #af6025; font-style: italic; font-size: 10px;">{html.escape(str(flavour))}</div>')

        return "".join(parts)

    def _build_header(self, name: str, base_type: str, rarity: str) -> str:
        """Build the header section with item name and base type."""
        rarity_color = get_rarity_color(rarity)

        parts = []

        # Name (if different from base type)
        if name and name != base_type:
            safe_name = html.escape(str(name))
            parts.append(
                f'<div style="text-align: center; font-weight: bold; color: {rarity_color}; '
                f'font-size: 14px; padding: 2px 0;">{safe_name}</div>'
            )

        # Base type
        if base_type:
            safe_base = html.escape(str(base_type))
            parts.append(
                f'<div style="text-align: center; color: {rarity_color}; '
                f'font-size: 13px; padding: 2px 0;">{safe_base}</div>'
            )
        elif name:
            # Only name, no base type
            safe_name = html.escape(str(name))
            parts.append(
                f'<div style="text-align: center; font-weight: bold; color: {rarity_color}; '
                f'font-size: 14px; padding: 2px 0;">{safe_name}</div>'
            )

        return "".join(parts)

    def _build_properties(self, item: Any) -> str:
        """Build the properties section (Item Level, Requirements)."""
        parts = []

        # Item Level
        ilvl = getattr(item, "item_level", None)
        if ilvl:
            parts.append(
                f'<div style="font-size: 11px;">'
                f'<span style="color: {POE_TOOLTIP_COLORS["property_name"]};">Item Level: </span>'
                f'<span style="color: {POE_TOOLTIP_COLORS["property_value"]};">{ilvl}</span>'
                f'</div>'
            )

        # Requirements
        requirements = getattr(item, "requirements", {}) or {}
        level_req = requirements.get("level") or requirements.get("Level")
        str_req = requirements.get("str") or requirements.get("Str")
        dex_req = requirements.get("dex") or requirements.get("Dex")
        int_req = requirements.get("int") or requirements.get("Int")

        req_parts = []
        if level_req:
            req_parts.append(f"Level {level_req}")
        if str_req:
            req_parts.append(f"{str_req} Str")
        if dex_req:
            req_parts.append(f"{dex_req} Dex")
        if int_req:
            req_parts.append(f"{int_req} Int")

        if req_parts:
            parts.append(
                f'<div style="font-size: 11px;">'
                f'<span style="color: {POE_TOOLTIP_COLORS["property_name"]};">Requires </span>'
                f'<span style="color: {POE_TOOLTIP_COLORS["property_value"]};">{", ".join(req_parts)}</span>'
                f'</div>'
            )

        # Quality
        quality = getattr(item, "quality", None)
        if quality and quality > 0:
            parts.append(
                f'<div style="font-size: 11px;">'
                f'<span style="color: {POE_TOOLTIP_COLORS["property_name"]};">Quality: </span>'
                f'<span style="color: {POE_TOOLTIP_COLORS["mod_value"]};">+{quality}%</span>'
                f'</div>'
            )

        return "".join(parts)

    def _build_mod_line(self, mod: str, is_implicit: bool = False) -> str:
        """Build a single mod line with tier information."""
        safe_mod = html.escape(str(mod))

        # Detect mod tier
        tier_result = detect_mod_tier(mod, is_implicit=is_implicit)

        parts = []

        # Tier info line (gray, smaller)
        if tier_result.tier is not None:
            tier_color = get_tier_color(tier_result.tier)
            mod_type = "Implicit Modifier" if is_implicit else ("Prefix" if "prefix" in str(tier_result.stat_type or "").lower() else "Suffix")

            # Build tier info like: Prefix Modifier "Name" (Tier: X) — Category
            tier_info = f'{mod_type} (Tier: {tier_result.tier})'
            if tier_result.stat_type:
                tier_info += f' — {tier_result.stat_type.replace("_", " ").title()}'

            parts.append(
                f'<div style="color: {POE_TOOLTIP_COLORS["mod_info"]}; font-size: 9px;">'
                f'{tier_info}</div>'
            )
        elif is_implicit:
            parts.append(
                f'<div style="color: {POE_TOOLTIP_COLORS["mod_info"]}; font-size: 9px;">'
                f'Implicit Modifier</div>'
            )

        # The actual mod text
        if tier_result.is_crafted:
            mod_color = POE_TOOLTIP_COLORS["crafted"]
        elif is_implicit:
            mod_color = POE_TOOLTIP_COLORS["implicit_label"]
        else:
            mod_color = POE_TOOLTIP_COLORS["mod_value"]

        parts.append(
            f'<div style="color: {mod_color}; font-size: 12px; font-weight: 500;">'
            f'{safe_mod}</div>'
        )

        return "".join(parts)

    def _build_enchant_line(self, mod: str) -> str:
        """Build an enchant mod line."""
        safe_mod = html.escape(str(mod))
        return (
            f'<div style="color: {POE_TOOLTIP_COLORS["mod_info"]}; font-size: 9px;">Enchant</div>'
            f'<div style="color: {POE_TOOLTIP_COLORS["enchant"]}; font-size: 12px;">{safe_mod}</div>'
        )

    def _build_status_flags(self, item: Any) -> str:
        """Build status flags section (Corrupted, Mirrored, etc.)."""
        parts = []

        if getattr(item, "is_corrupted", False):
            parts.append(
                f'<div style="color: {POE_TOOLTIP_COLORS["corrupted"]}; font-weight: bold; '
                f'text-align: center; font-size: 12px;">Corrupted</div>'
            )

        if getattr(item, "is_mirrored", False):
            parts.append(
                f'<div style="color: {POE_TOOLTIP_COLORS["mirrored"]}; font-weight: bold; '
                f'text-align: center; font-size: 12px;">Mirrored</div>'
            )

        if getattr(item, "is_fractured", False):
            parts.append(
                f'<div style="color: {POE_TOOLTIP_COLORS["fractured"]}; '
                f'text-align: center; font-size: 11px;">Fractured</div>'
            )

        if getattr(item, "is_synthesised", False):
            parts.append(
                f'<div style="color: #60a0d0; text-align: center; font-size: 11px;">Synthesised</div>'
            )

        # Influences
        influences = getattr(item, "influences", []) or []
        for influence in influences:
            parts.append(
                f'<div style="color: #ddc0a0; text-align: center; font-size: 11px;">'
                f'{html.escape(str(influence))} Item</div>'
            )

        return "".join(parts)

    def _separator(self) -> str:
        """Return an HTML separator line."""
        return (
            f'<div style="border-top: 1px solid {POE_TOOLTIP_COLORS["separator"]}; '
            f'margin: 4px 0; height: 1px;"></div>'
        )


class ItemTooltipMixin:
    """
    Mixin class to add PoE-style item tooltip support to any widget.

    The widget must:
    1. Call _init_item_tooltip() in __init__
    2. Implement _get_item_at_pos(pos: QPoint) -> Optional[ParsedItem]
    3. Call _handle_tooltip_mouse_move(event) in mouseMoveEvent
    """

    def _init_item_tooltip(self) -> None:
        """Initialize tooltip support. Call this in __init__."""
        self._tooltip_timer = QTimer()
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._show_item_tooltip)
        self._tooltip_item: Optional[Any] = None
        self._tooltip_pos = QPoint()
        self._alt_was_pressed = False

        # Track mouse to enable/disable tooltip
        self.setMouseTracking(True)

    def _get_item_at_pos(self, pos: QPoint) -> Optional[Any]:
        """
        Override this to return the item at the given widget position.

        Args:
            pos: Position in widget coordinates

        Returns:
            ParsedItem or similar, or None if no item at position
        """
        raise NotImplementedError("Subclass must implement _get_item_at_pos")

    def _handle_tooltip_mouse_move(self, pos: QPoint, global_pos: QPoint) -> None:
        """
        Call this from mouseMoveEvent to handle tooltip display.

        Args:
            pos: Mouse position in widget coordinates
            global_pos: Mouse position in global screen coordinates
        """
        # Check if Alt is pressed
        modifiers = QApplication.keyboardModifiers()
        alt_pressed = bool(modifiers & Qt.KeyboardModifier.AltModifier)

        if alt_pressed:
            # Get item at position
            item = self._get_item_at_pos(pos)

            if item is not None:
                self._tooltip_item = item
                self._tooltip_pos = global_pos

                # Show immediately if Alt just pressed, otherwise short delay
                if not self._alt_was_pressed:
                    self._show_item_tooltip()
                else:
                    self._tooltip_timer.start(50)  # Short delay for smooth updates
            else:
                self._hide_item_tooltip()
        else:
            self._hide_item_tooltip()

        self._alt_was_pressed = alt_pressed

    def _show_item_tooltip(self) -> None:
        """Show the tooltip for the current item."""
        if self._tooltip_item is not None:
            tooltip = PoEItemTooltip.instance()
            tooltip.show_for_item(self._tooltip_item, self._tooltip_pos)

    def _hide_item_tooltip(self) -> None:
        """Hide the tooltip."""
        self._tooltip_timer.stop()
        self._tooltip_item = None
        tooltip = PoEItemTooltip.instance()
        tooltip.hide_after_delay(50)


def show_item_tooltip(item: Any, global_pos: QPoint) -> None:
    """
    Convenience function to show a tooltip for an item.

    Args:
        item: ParsedItem or similar object
        global_pos: Global screen position
    """
    tooltip = PoEItemTooltip.instance()
    tooltip.show_for_item(item, global_pos)


def hide_item_tooltip() -> None:
    """Convenience function to hide the item tooltip."""
    tooltip = PoEItemTooltip.instance()
    tooltip.hide_after_delay(50)
