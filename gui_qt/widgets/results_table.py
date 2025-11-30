"""
gui_qt.widgets.results_table

PyQt6 table widget for displaying price check results.
"""

from __future__ import annotations

import html
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QPoint
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (
    QTableView,
    QWidget,
    QAbstractItemView,
    QMenu,
    QApplication,
    QHeaderView,
)

from gui_qt.styles import COLORS, get_rarity_color, get_tier_color, TIER_COLORS
from gui_qt.widgets.poe_item_tooltip import ItemTooltipMixin
from core.mod_tier_detector import detect_mod_tier

logger = logging.getLogger(__name__)

# Trend colors (colorblind-safe)
TREND_COLORS = {
    "up": "#4CAF50",  # Green
    "down": "#F44336",  # Red
    "stable": "#9E9E9E",  # Gray
}


def build_item_tooltip_html(item: Any) -> str:
    """
    Build HTML tooltip content for an item preview.

    Args:
        item: ParsedItem or similar object with item properties

    Returns:
        HTML string for rich tooltip display
    """
    if item is None:
        return ""

    parts = []

    # Item name with rarity color
    name = getattr(item, "name", "") or getattr(item, "base_type", "Unknown")
    safe_name = html.escape(str(name))
    rarity = getattr(item, "rarity", "Normal")
    rarity_color = get_rarity_color(rarity)

    parts.append(
        f'<div style="font-weight: bold; color: {rarity_color}; font-size: 12px;">{safe_name}</div>'
    )

    # Base type (if different from name)
    base_type = getattr(item, "base_type", "")
    if base_type and base_type != name:
        safe_base = html.escape(str(base_type))
        parts.append(f'<div style="color: #888; font-size: 10px;">{safe_base}</div>')

    # Item properties
    props = []
    ilvl = getattr(item, "item_level", None) or getattr(item, "ilvl", None)
    if ilvl:
        props.append(f"iLvl {ilvl}")

    links = getattr(item, "links", None) or getattr(item, "max_links", None)
    if links and int(links) > 0:
        props.append(f"{links}L")

    quality = getattr(item, "quality", None)
    if quality:
        props.append(f"+{quality}%")

    if props:
        parts.append(f'<div style="color: #aaa; font-size: 10px;">{" | ".join(props)}</div>')

    # Corrupted status
    if getattr(item, "corrupted", False):
        parts.append(f'<div style="color: {COLORS["corrupted"]}; font-weight: bold;">Corrupted</div>')

    # Implicit mods (with tier highlighting)
    implicits = getattr(item, "implicits", []) or getattr(item, "implicit_mods", [])
    if implicits:
        parts.append('<hr style="border: 1px solid #444; margin: 4px 0;">')
        for mod in implicits[:3]:  # Limit to 3 for tooltip
            safe_mod = html.escape(str(mod))
            tier_result = detect_mod_tier(mod, is_implicit=True)
            tier_prefix = ""
            if tier_result.tier:
                tier_color = get_tier_color(tier_result.tier)
                tier_prefix = f'<span style="color: {tier_color}; font-weight: bold;">[{tier_result.tier_label}]</span> '
            parts.append(
                f'<div style="color: {TIER_COLORS["implicit"]}; font-size: 10px;">{tier_prefix}{safe_mod}</div>'
            )
        if len(implicits) > 3:
            parts.append(f'<div style="color: #666; font-size: 9px;">...+{len(implicits) - 3} more</div>')

    # Explicit mods (with tier highlighting)
    explicits = getattr(item, "explicits", []) or getattr(item, "explicit_mods", []) or getattr(item, "mods", [])
    if explicits:
        parts.append('<hr style="border: 1px solid #444; margin: 4px 0;">')
        for mod in explicits[:5]:  # Limit to 5 for tooltip
            safe_mod = html.escape(str(mod))
            tier_result = detect_mod_tier(mod, is_implicit=False)

            # Determine color
            if tier_result.is_crafted:
                mod_color = TIER_COLORS["crafted"]
            elif tier_result.tier:
                mod_color = get_tier_color(tier_result.tier)
            else:
                mod_color = COLORS["text"]

            # Build tier prefix
            tier_prefix = ""
            if tier_result.tier:
                tier_color = get_tier_color(tier_result.tier)
                tier_prefix = f'<span style="color: {tier_color}; font-weight: bold;">[{tier_result.tier_label}]</span> '

            parts.append(
                f'<div style="color: {mod_color}; font-size: 10px;">{tier_prefix}{safe_mod}</div>'
            )
        if len(explicits) > 5:
            parts.append(f'<div style="color: #666; font-size: 9px;">...+{len(explicits) - 5} more</div>')

    return "".join(parts)


class ResultsTableModel(QAbstractTableModel):
    """Table model for price check results."""

    # Column definitions: (key, display_name, default_width)
    COLUMNS = [
        ("item_name", "Item Name", 180),
        ("variant", "Variant", 100),
        ("links", "Links", 60),
        ("chaos_value", "Chaos", 80),
        ("profit", "Profit", 70),
        ("divine_value", "Divine", 80),
        ("trend_7d", "7d Trend", 75),
        ("listing_count", "Listings", 70),
        ("source", "Source", 100),
        ("upgrade", "Upgrade", 70),
        ("price_explanation", "Explanation", 0),  # Hidden
    ]

    # Profit column colors
    PROFIT_COLORS = {
        "positive": "#4CAF50",  # Green
        "negative": "#F44336",  # Red
        "neutral": "#9E9E9E",   # Gray
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._hidden_columns: set[str] = {"price_explanation"}
        self._trend_calculator = None
        self._league = "Standard"

    @property
    def columns(self) -> List[str]:
        """Return list of column keys."""
        return [col[0] for col in self.COLUMNS]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.COLUMNS)

    @property
    def trend_calculator(self):
        """Lazy-load trend calculator."""
        if self._trend_calculator is None:
            try:
                from core.price_trend_calculator import get_trend_calculator

                self._trend_calculator = get_trend_calculator()
            except Exception as e:
                logger.warning(f"Failed to load trend calculator: {e}")
        return self._trend_calculator

    def set_league(self, league: str) -> None:
        """Set the current league for trend calculations."""
        self._league = league

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        row_data = self._data[index.row()]
        col_key = self.COLUMNS[index.column()][0]
        value = row_data.get(col_key, "")

        if role == Qt.ItemDataRole.DisplayRole:
            # Format numeric values
            if col_key in ("chaos_value", "divine_value"):
                try:
                    return f"{float(value):.1f}" if value else ""
                except (ValueError, TypeError):
                    return str(value) if value else ""

            # Profit column - calculate from chaos_value and purchase_price
            if col_key == "profit":
                purchase_price = row_data.get("purchase_price")
                chaos_val = row_data.get("chaos_value", 0)
                if purchase_price is not None:
                    try:
                        purchase = float(purchase_price)
                        current = float(chaos_val) if chaos_val else 0
                        profit = current - purchase
                        sign = "+" if profit >= 0 else ""
                        return f"{sign}{profit:.1f}c"
                    except (ValueError, TypeError):
                        pass
                return ""

            # Trend column
            if col_key == "trend_7d":
                trend = row_data.get("_trend")
                if trend:
                    return trend.display_text
                return ""

            return str(value) if value else ""

        elif role == Qt.ItemDataRole.ForegroundRole:
            # Profit column coloring
            if col_key == "profit":
                purchase_price = row_data.get("purchase_price")
                chaos_val = row_data.get("chaos_value", 0)
                if purchase_price is not None:
                    try:
                        purchase = float(purchase_price)
                        current = float(chaos_val) if chaos_val else 0
                        profit = current - purchase
                        if profit > 0:
                            return QBrush(QColor(self.PROFIT_COLORS["positive"]))
                        elif profit < 0:
                            return QBrush(QColor(self.PROFIT_COLORS["negative"]))
                        else:
                            return QBrush(QColor(self.PROFIT_COLORS["neutral"]))
                    except (ValueError, TypeError):
                        pass
                return QBrush(QColor(self.PROFIT_COLORS["neutral"]))

            # Trend column coloring
            if col_key == "trend_7d":
                trend = row_data.get("_trend")
                if trend:
                    color = TREND_COLORS.get(trend.trend, TREND_COLORS["stable"])
                    return QBrush(QColor(color))

            # Color based on value
            chaos_val = row_data.get("chaos_value", 0)
            try:
                chaos_val = float(chaos_val) if chaos_val else 0
            except (ValueError, TypeError):
                chaos_val = 0

            if chaos_val >= 100:
                return QBrush(QColor(COLORS["high_value"]))
            elif chaos_val >= 10:
                return QBrush(QColor(COLORS["medium_value"]))

            # Upgrade indicator
            if col_key == "upgrade" and value:
                return QBrush(QColor(COLORS["upgrade"]))

        elif role == Qt.ItemDataRole.BackgroundRole:
            # Highlight upgrade rows
            if row_data.get("upgrade"):
                return QBrush(QColor("#2a3a2a"))  # Dark green tint

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col_key in ("chaos_value", "divine_value", "listing_count", "links", "trend_7d", "profit"):
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ToolTipRole:
            # Item preview tooltip for item_name column
            if col_key == "item_name":
                item = row_data.get("_item")
                if item:
                    return build_item_tooltip_html(item)
                # Fallback: simple tooltip with available info
                parts = [row_data.get("item_name", "")]
                variant = row_data.get("variant")
                if variant:
                    parts.append(f"Variant: {variant}")
                chaos = row_data.get("chaos_value")
                if chaos:
                    parts.append(f"Price: {chaos:.1f}c")
                return "\n".join(parts) if parts else None

            # Trend tooltip
            if col_key == "trend_7d":
                trend = row_data.get("_trend")
                if trend:
                    return trend.tooltip
                return "No trend data available"

            # Price tooltip - show explanation if available
            if col_key in ("chaos_value", "divine_value"):
                explanation = row_data.get("price_explanation")
                if explanation:
                    try:
                        import json
                        exp_data = json.loads(explanation)
                        if isinstance(exp_data, dict):
                            parts = []
                            if exp_data.get("method"):
                                parts.append(f"Method: {exp_data['method']}")
                            if exp_data.get("confidence"):
                                parts.append(f"Confidence: {exp_data['confidence']}")
                            if exp_data.get("listings_used"):
                                parts.append(f"Based on {exp_data['listings_used']} listings")
                            return "\n".join(parts) if parts else None
                    except (json.JSONDecodeError, TypeError):
                        pass

        elif role == Qt.ItemDataRole.UserRole:
            # Return full row data for selection handling
            return row_data

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.COLUMNS[section][1]
            else:
                return str(section + 1)
        return None

    def set_data(self, data: List[Dict[str, Any]], calculate_trends: bool = True) -> None:
        """Set the table data.

        Args:
            data: List of row dictionaries
            calculate_trends: Whether to calculate price trends (default True)
        """
        self.beginResetModel()
        self._data = data

        # Calculate trends for each item
        if calculate_trends and self.trend_calculator:
            for row in self._data:
                item_name = row.get("item_name", "")
                if item_name:
                    try:
                        trend = self.trend_calculator.get_trend(
                            item_name, self._league, days=7
                        )
                        row["_trend"] = trend
                    except Exception as e:
                        logger.debug(f"Failed to get trend for {item_name}: {e}")

        self.endResetModel()

    def get_row(self, row: int) -> Optional[Dict[str, Any]]:
        """Get data for a specific row."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Sort by column."""
        if not self._data:
            return

        col_key = self.COLUMNS[column][0]
        reverse = order == Qt.SortOrder.DescendingOrder

        def sort_key(row: Dict[str, Any]) -> Any:
            val = row.get(col_key, "")
            # Try numeric sort
            try:
                return float(val) if val else 0
            except (ValueError, TypeError):
                return str(val).lower()

        self.beginResetModel()
        self._data.sort(key=sort_key, reverse=reverse)
        self.endResetModel()


class ResultsTableWidget(QTableView, ItemTooltipMixin):
    """Table widget for displaying price check results.

    Supports Alt+hover to show PoE-style item tooltips.
    """

    row_selected = pyqtSignal(dict)  # Emits selected row data (for single selection)
    rows_selected = pyqtSignal(list)  # Emits list of selected row data (for multi-selection)
    compare_requested = pyqtSignal(list)  # Request to compare selected items
    pin_requested = pyqtSignal(list)  # Request to pin selected items
    export_selected_requested = pyqtSignal(list)  # Request to export selected items
    column_order_changed = pyqtSignal(list)  # Emits new column order (list of keys)

    # Storage file for column settings
    COLUMN_CONFIG_FILE = "column_config.json"

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Setup model
        self._model = ResultsTableModel(self)
        self.setModel(self._model)

        # Configure view
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setShowGrid(False)

        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Configure header
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)
        header.setSortIndicatorShown(True)

        # Enable header context menu for column visibility
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_context_menu)

        # Connect to section moved for persistence
        header.sectionMoved.connect(self._on_section_moved)

        # Set default column widths
        for i, (key, name, width) in enumerate(ResultsTableModel.COLUMNS):
            if width > 0:
                self.setColumnWidth(i, width)
            else:
                self.setColumnHidden(i, True)

        # Load saved column configuration
        self._load_column_config()

        # Connect selection
        self.selectionModel().currentRowChanged.connect(self._on_row_changed)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # Initialize Alt+hover tooltip support
        self._init_item_tooltip()

    @property
    def columns(self) -> List[str]:
        """Return list of column keys."""
        return self._model.columns

    def set_league(self, league: str) -> None:
        """Set the current league for trend calculations."""
        self._model.set_league(league)

    def set_data(self, data: List[Dict[str, Any]], calculate_trends: bool = True) -> None:
        """Set the table data."""
        self._model.set_data(data, calculate_trends=calculate_trends)

    def get_selected_row(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected row data."""
        indexes = self.selectionModel().selectedRows()
        if indexes:
            return self._model.get_row(indexes[0].row())
        return None

    def set_column_visible(self, column: str, visible: bool) -> None:
        """Show or hide a column."""
        for i, (key, _, _) in enumerate(ResultsTableModel.COLUMNS):
            if key == column:
                self.setColumnHidden(i, not visible)
                break

    def _on_row_changed(self, current: QModelIndex, previous: QModelIndex) -> None:
        """Handle row selection change."""
        if current.isValid():
            row_data = self._model.get_row(current.row())
            if row_data:
                self.row_selected.emit(row_data)

    def _on_selection_changed(self, selected, deselected) -> None:
        """Handle selection changed - emit all selected rows."""
        selected_rows = self.get_selected_rows()
        self.rows_selected.emit(selected_rows)

    def get_selected_rows(self) -> List[Dict[str, Any]]:
        """Get all currently selected row data."""
        indexes = self.selectionModel().selectedRows()
        rows = []
        for index in indexes:
            row_data = self._model.get_row(index.row())
            if row_data:
                rows.append(row_data)
        return rows

    def get_selection_count(self) -> int:
        """Get number of selected rows."""
        return len(self.selectionModel().selectedRows())

    def select_all(self) -> None:
        """Select all rows."""
        self.selectAll()

    def clear_selection(self) -> None:
        """Clear all selection."""
        self.clearSelection()

    # ------------------------------------------------------------------
    # Alt+Hover Tooltip Support (ItemTooltipMixin implementation)
    # ------------------------------------------------------------------

    def _get_item_at_pos(self, pos: QPoint) -> Optional[Any]:
        """Get the ParsedItem at the given viewport position.

        Required by ItemTooltipMixin.
        """
        # Get the index at the viewport position
        index = self.indexAt(pos)
        if not index.isValid():
            return None

        # Get the row data
        row_data = self._model.get_row(index.row())
        if row_data is None:
            return None

        # Return the stored ParsedItem if available
        return row_data.get("_item")

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move to show/hide Alt+hover tooltip."""
        # Let the base class handle the event first
        super().mouseMoveEvent(event)

        # Handle tooltip display (from ItemTooltipMixin)
        self._handle_tooltip_mouse_move(event.pos(), event.globalPosition().toPoint())

    def _show_context_menu(self, position) -> None:
        """Show context menu for batch operations."""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return

        menu = QMenu(self)
        count = len(selected_rows)

        # Single item actions
        if count == 1:
            inspect_action = menu.addAction("Inspect Item")
            inspect_action.triggered.connect(
                lambda: self.row_selected.emit(selected_rows[0])
            )

        # Multi-item actions
        if count >= 2:
            compare_action = menu.addAction(f"Compare {count} Items")
            compare_action.triggered.connect(
                lambda: self.compare_requested.emit(selected_rows)
            )
            if count > 3:
                compare_action.setEnabled(False)
                compare_action.setText(f"Compare Items (max 3)")

        menu.addSeparator()

        # Pin action
        pin_action = menu.addAction(f"Pin {count} Item(s)")
        pin_action.triggered.connect(
            lambda: self.pin_requested.emit(selected_rows)
        )

        # Copy actions
        copy_menu = menu.addMenu("Copy")
        copy_names_action = copy_menu.addAction("Item Names")
        copy_names_action.triggered.connect(
            lambda: self._copy_to_clipboard([r.get("item_name", "") for r in selected_rows])
        )
        copy_prices_action = copy_menu.addAction("Prices (Chaos)")
        copy_prices_action.triggered.connect(
            lambda: self._copy_to_clipboard([str(r.get("chaos_value", "")) for r in selected_rows])
        )
        copy_all_action = copy_menu.addAction("Selected Rows (TSV)")
        copy_all_action.triggered.connect(
            lambda: self._copy_selected_tsv(selected_rows)
        )

        menu.addSeparator()

        # Export action
        export_action = menu.addAction(f"Export {count} Item(s)...")
        export_action.triggered.connect(
            lambda: self.export_selected_requested.emit(selected_rows)
        )

        # Select all action
        menu.addSeparator()
        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self.select_all)

        menu.exec(self.viewport().mapToGlobal(position))

    def _copy_to_clipboard(self, items: List[str]) -> None:
        """Copy items to clipboard, one per line."""
        text = "\n".join(str(item) for item in items if item)
        QApplication.clipboard().setText(text)

    def _copy_selected_tsv(self, rows: List[Dict[str, Any]]) -> None:
        """Copy selected rows as TSV to clipboard."""
        if not rows:
            return

        # Get visible columns
        visible_cols = []
        for i, (key, name, _) in enumerate(ResultsTableModel.COLUMNS):
            if not self.isColumnHidden(i):
                visible_cols.append((key, name))

        # Build TSV
        lines = []
        # Header
        lines.append("\t".join(name for _, name in visible_cols))
        # Data rows
        for row in rows:
            values = []
            for key, _ in visible_cols:
                val = row.get(key, "")
                values.append(str(val) if val is not None else "")
            lines.append("\t".join(values))

        QApplication.clipboard().setText("\n".join(lines))

    def to_tsv(self, include_header: bool = True) -> str:
        """Export table data as TSV string."""
        lines = []

        # Get visible columns
        visible_cols = []
        for i, (key, name, _) in enumerate(ResultsTableModel.COLUMNS):
            if not self.isColumnHidden(i):
                visible_cols.append((i, key, name))

        if include_header:
            header = "\t".join(name for _, _, name in visible_cols)
            lines.append(header)

        for row in range(self._model.rowCount()):
            values = []
            for col_idx, key, _ in visible_cols:
                index = self._model.index(row, col_idx)
                value = self._model.data(index, Qt.ItemDataRole.DisplayRole)
                values.append(str(value) if value else "")
            lines.append("\t".join(values))

        return "\n".join(lines)

    def export_tsv(self, path: str | Path) -> None:
        """Export table data to TSV file."""
        tsv = self.to_tsv(include_header=True)
        Path(path).write_text(tsv, encoding="utf-8")

    # ------------------------------------------------------------------
    # Column Configuration (Order & Visibility)
    # ------------------------------------------------------------------

    def _get_config_path(self) -> Path:
        """Get the path to the column config file."""
        from core.config import get_config_dir
        return get_config_dir() / self.COLUMN_CONFIG_FILE

    def _load_column_config(self) -> None:
        """Load saved column order and visibility from disk."""
        try:
            config_path = self._get_config_path()
            if not config_path.exists():
                return

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            header = self.horizontalHeader()

            # Restore column order
            if "order" in config:
                saved_order = config["order"]
                # Map column keys to logical indices
                key_to_logical = {
                    col[0]: i for i, col in enumerate(ResultsTableModel.COLUMNS)
                }

                # Move sections to match saved order
                for visual_idx, key in enumerate(saved_order):
                    if key in key_to_logical:
                        logical_idx = key_to_logical[key]
                        current_visual = header.visualIndex(logical_idx)
                        if current_visual != visual_idx:
                            header.moveSection(current_visual, visual_idx)

            # Restore column visibility
            if "hidden" in config:
                for key in config["hidden"]:
                    for i, (col_key, _, _) in enumerate(ResultsTableModel.COLUMNS):
                        if col_key == key:
                            self.setColumnHidden(i, True)
                            break

            # Restore column widths
            if "widths" in config:
                for key, width in config["widths"].items():
                    for i, (col_key, _, _) in enumerate(ResultsTableModel.COLUMNS):
                        if col_key == key:
                            self.setColumnWidth(i, width)
                            break

            logger.debug("Column configuration loaded")
        except Exception as e:
            logger.warning(f"Failed to load column config: {e}")

    def _save_column_config(self) -> None:
        """Save current column order and visibility to disk."""
        try:
            header = self.horizontalHeader()
            config = {}

            # Save column order (by key)
            order = []
            for visual_idx in range(header.count()):
                logical_idx = header.logicalIndex(visual_idx)
                key = ResultsTableModel.COLUMNS[logical_idx][0]
                order.append(key)
            config["order"] = order

            # Save hidden columns
            hidden = []
            for i, (key, _, _) in enumerate(ResultsTableModel.COLUMNS):
                if self.isColumnHidden(i):
                    hidden.append(key)
            config["hidden"] = hidden

            # Save column widths
            widths = {}
            for i, (key, _, default_width) in enumerate(ResultsTableModel.COLUMNS):
                current_width = self.columnWidth(i)
                if current_width != default_width and current_width > 0:
                    widths[key] = current_width
            if widths:
                config["widths"] = widths

            # Write to disk
            config_path = self._get_config_path()
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            logger.debug("Column configuration saved")
        except Exception as e:
            logger.warning(f"Failed to save column config: {e}")

    def _on_section_moved(self, logical_index: int, old_visual: int, new_visual: int) -> None:
        """Handle column being dragged to a new position."""
        self._save_column_config()
        self.column_order_changed.emit(self.get_column_order())

    def _show_header_context_menu(self, position) -> None:
        """Show context menu for column visibility and reset."""
        header = self.horizontalHeader()
        menu = QMenu(self)

        # Column visibility submenu
        visibility_menu = menu.addMenu("Show/Hide Columns")
        for i, (key, name, _) in enumerate(ResultsTableModel.COLUMNS):
            # Skip the hidden price_explanation column
            if key == "price_explanation":
                continue

            action = visibility_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(i))
            action.setData(i)
            action.triggered.connect(
                lambda checked, idx=i: self._toggle_column_visibility(idx, checked)
            )

        menu.addSeparator()

        # Reset column order
        reset_order_action = menu.addAction("Reset Column Order")
        reset_order_action.triggered.connect(self.reset_column_order)

        # Reset all (order + visibility + widths)
        reset_all_action = menu.addAction("Reset All to Defaults")
        reset_all_action.triggered.connect(self.reset_column_config)

        menu.exec(header.mapToGlobal(position))

    def _toggle_column_visibility(self, column_index: int, visible: bool) -> None:
        """Toggle visibility of a column and save config."""
        self.setColumnHidden(column_index, not visible)
        self._save_column_config()

    def reset_column_order(self) -> None:
        """Reset columns to their default order."""
        header = self.horizontalHeader()

        # Move each column back to its original logical position
        for logical_idx in range(header.count()):
            current_visual = header.visualIndex(logical_idx)
            if current_visual != logical_idx:
                header.moveSection(current_visual, logical_idx)

        self._save_column_config()
        self.column_order_changed.emit(self.get_column_order())

    def reset_column_config(self) -> None:
        """Reset all column settings to defaults (order, visibility, widths)."""
        header = self.horizontalHeader()

        # Reset order
        for logical_idx in range(header.count()):
            current_visual = header.visualIndex(logical_idx)
            if current_visual != logical_idx:
                header.moveSection(current_visual, logical_idx)

        # Reset visibility and widths
        for i, (key, name, default_width) in enumerate(ResultsTableModel.COLUMNS):
            if default_width > 0:
                self.setColumnHidden(i, False)
                self.setColumnWidth(i, default_width)
            else:
                self.setColumnHidden(i, True)

        # Delete config file to reset to defaults
        try:
            config_path = self._get_config_path()
            if config_path.exists():
                config_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete column config: {e}")

        self.column_order_changed.emit(self.get_column_order())

    def get_column_order(self) -> List[str]:
        """Get the current visual order of columns as a list of keys."""
        header = self.horizontalHeader()
        order = []
        for visual_idx in range(header.count()):
            logical_idx = header.logicalIndex(visual_idx)
            key = ResultsTableModel.COLUMNS[logical_idx][0]
            order.append(key)
        return order

    def set_column_order(self, order: List[str]) -> None:
        """
        Set the column order from a list of keys.

        Args:
            order: List of column keys in desired visual order
        """
        header = self.horizontalHeader()
        key_to_logical = {
            col[0]: i for i, col in enumerate(ResultsTableModel.COLUMNS)
        }

        for visual_idx, key in enumerate(order):
            if key in key_to_logical:
                logical_idx = key_to_logical[key]
                current_visual = header.visualIndex(logical_idx)
                if current_visual != visual_idx:
                    header.moveSection(current_visual, visual_idx)

        self._save_column_config()
        self.column_order_changed.emit(self.get_column_order())
