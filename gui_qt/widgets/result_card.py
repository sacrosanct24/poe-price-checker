"""
Result Card - Card-based view for price check results.

Provides a visual card representation of items as an alternative
to the table view, optimized for browsing and quick scanning.

Usage:
    from gui_qt.widgets.result_card import ResultCard, ResultCardsView

    # Create a card for an item
    card = ResultCard(item_data)

    # Create a scrollable cards view
    cards_view = ResultCardsView()
    cards_view.set_data(results_list)
"""

from typing import Any, Dict, List, Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QMouseEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QGridLayout,
    QSizePolicy,
    QGraphicsDropShadowEffect,
    QMenu,
    QApplication,
)

from gui_qt.styles import COLORS, get_rarity_color
from gui_qt.design_system import (
    Spacing,
    BorderRadius,
    Duration,
    FontSize,
    FontWeight,
    Elevation,
)


class ResultCard(QFrame):
    """
    Visual card representation of a price check result.

    Displays item info in a compact, scannable format with
    hover effects and click handling.
    """

    clicked = pyqtSignal(dict)  # Emits card data when clicked
    double_clicked = pyqtSignal(dict)  # Emits card data on double-click
    context_menu_requested = pyqtSignal(dict, QPoint)  # For right-click menu

    # Card dimensions
    CARD_WIDTH = 220
    CARD_HEIGHT = 160
    CARD_SPACING = Spacing.MD

    def __init__(
        self,
        data: Dict[str, Any],
        parent: Optional[QWidget] = None,
    ):
        """
        Initialize result card.

        Args:
            data: Dictionary with item data (item_name, chaos_value, etc.)
            parent: Parent widget
        """
        super().__init__(parent)

        self._data = data
        self._selected = False
        self._hovered = False

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Set up the card UI."""
        self.setFixedSize(self.CARD_WIDTH, self.CARD_HEIGHT)
        self.setObjectName("resultCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)

        # Item name (top section)
        self._name_label = QLabel()
        self._name_label.setWordWrap(True)
        self._name_label.setMaximumHeight(40)
        self._name_label.setObjectName("cardItemName")

        item_name = self._data.get("item_name", "Unknown Item")
        rarity = self._data.get("rarity", "Normal")
        rarity_color = get_rarity_color(rarity)

        self._name_label.setText(item_name)
        self._name_label.setStyleSheet(f"""
            QLabel#cardItemName {{
                color: {rarity_color};
                font-size: {FontSize.BASE}px;
                font-weight: {FontWeight.SEMIBOLD};
            }}
        """)
        layout.addWidget(self._name_label)

        # Variant/Details (if available)
        variant = self._data.get("variant", "")
        links = self._data.get("links", "")
        details = []
        if variant:
            details.append(variant)
        try:
            if links and int(links) > 0:
                details.append(f"{links}L")
        except (ValueError, TypeError):
            pass  # Invalid links value

        if details:
            self._details_label = QLabel(" | ".join(details))
            self._details_label.setObjectName("cardDetails")
            self._details_label.setStyleSheet(f"""
                QLabel#cardDetails {{
                    color: {COLORS['text_secondary']};
                    font-size: {FontSize.SM}px;
                }}
            """)
            layout.addWidget(self._details_label)

        # Spacer
        layout.addStretch()

        # Price section (bottom)
        price_layout = QHBoxLayout()
        price_layout.setSpacing(Spacing.SM)

        # Chaos price (large)
        chaos_value = self._data.get("chaos_value", 0)
        try:
            chaos_float = float(chaos_value) if chaos_value else 0
            chaos_text = f"{chaos_float:.1f}c"
        except (ValueError, TypeError):
            chaos_text = str(chaos_value) if chaos_value else "—"

        self._price_label = QLabel(chaos_text)
        self._price_label.setObjectName("cardPrice")

        # Determine price color based on value
        if chaos_float >= 100:
            price_color = COLORS["high_value"]
        elif chaos_float >= 10:
            price_color = COLORS["medium_value"]
        else:
            price_color = COLORS["text"]

        self._price_label.setStyleSheet(f"""
            QLabel#cardPrice {{
                color: {price_color};
                font-size: {FontSize.XL}px;
                font-weight: {FontWeight.BOLD};
            }}
        """)
        price_layout.addWidget(self._price_label)

        price_layout.addStretch()

        # Divine equivalent (if significant)
        divine_value = self._data.get("divine_value", 0)
        try:
            divine_float = float(divine_value) if divine_value else 0
            if divine_float >= 0.1:
                self._divine_label = QLabel(f"({divine_float:.2f}d)")
                self._divine_label.setObjectName("cardDivine")
                self._divine_label.setStyleSheet(f"""
                    QLabel#cardDivine {{
                        color: {COLORS['divine']};
                        font-size: {FontSize.SM}px;
                    }}
                """)
                price_layout.addWidget(self._divine_label)
        except (ValueError, TypeError):
            pass

        layout.addLayout(price_layout)

        # Trend indicator (if available)
        trend = self._data.get("_trend")
        if trend:
            trend_layout = QHBoxLayout()
            trend_layout.setSpacing(Spacing.XS)

            trend_colors = {
                "up": "#4CAF50",
                "down": "#F44336",
                "stable": "#9E9E9E",
            }
            trend_color = trend_colors.get(trend.trend, trend_colors["stable"])

            trend_label = QLabel(trend.display_text)
            trend_label.setStyleSheet(f"""
                color: {trend_color};
                font-size: {FontSize.XS}px;
            """)
            trend_layout.addWidget(trend_label)
            trend_layout.addStretch()

            layout.addLayout(trend_layout)

        # Source indicator
        source = self._data.get("source", "")
        if source:
            source_label = QLabel(source)
            source_label.setObjectName("cardSource")
            source_label.setStyleSheet(f"""
                QLabel#cardSource {{
                    color: {COLORS['text_muted']};
                    font-size: {FontSize.XS}px;
                }}
            """)
            layout.addWidget(source_label)

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(Elevation.LEVEL_1 * 2)
        shadow.setOffset(0, Elevation.LEVEL_1)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def _apply_style(self) -> None:
        """Apply card styling."""
        self.setStyleSheet(f"""
            QFrame#resultCard {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {BorderRadius.MD}px;
            }}
            QFrame#resultCard:hover {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['surface_variant']};
            }}
        """)

    def set_selected(self, selected: bool) -> None:
        """Set selection state."""
        self._selected = selected
        if selected:
            self.setStyleSheet(f"""
                QFrame#resultCard {{
                    background-color: {COLORS['surface_variant']};
                    border: 2px solid {COLORS['primary']};
                    border-radius: {BorderRadius.MD}px;
                }}
            """)
        else:
            self._apply_style()

    def is_selected(self) -> bool:
        """Check if card is selected."""
        return self._selected

    def get_data(self) -> Dict[str, Any]:
        """Get the card's data."""
        return self._data

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._data)
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(
                self._data,
                event.globalPosition().toPoint()
            )
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self._data)
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event) -> None:
        """Handle mouse enter."""
        self._hovered = True
        # Update shadow for hover state
        shadow = self.graphicsEffect()
        if isinstance(shadow, QGraphicsDropShadowEffect):
            shadow.setBlurRadius(Elevation.LEVEL_2 * 2)
            shadow.setOffset(0, Elevation.LEVEL_2)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leave."""
        self._hovered = False
        # Reset shadow
        shadow = self.graphicsEffect()
        if isinstance(shadow, QGraphicsDropShadowEffect):
            shadow.setBlurRadius(Elevation.LEVEL_1 * 2)
            shadow.setOffset(0, Elevation.LEVEL_1)
        super().leaveEvent(event)


class ResultCardsView(QScrollArea):
    """
    Scrollable grid view of result cards.

    Displays price check results as a grid of visual cards
    with support for selection, sorting, and filtering.
    """

    card_clicked = pyqtSignal(dict)  # Single card clicked
    card_double_clicked = pyqtSignal(dict)  # Card double-clicked
    cards_selected = pyqtSignal(list)  # Multiple cards selected
    compare_requested = pyqtSignal(list)  # Compare selected cards
    export_requested = pyqtSignal(list)  # Export selected cards

    # Grid configuration
    MIN_COLUMNS = 1
    MAX_COLUMNS = 6

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize cards view."""
        super().__init__(parent)

        self._data: List[Dict[str, Any]] = []
        self._cards: List[ResultCard] = []
        self._selected_indices: set = set()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the scrollable area."""
        # Configure scroll area
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setObjectName("cardsScrollArea")

        # Container widget
        self._container = QWidget()
        self._container.setObjectName("cardsContainer")
        self.setWidget(self._container)

        # Grid layout for cards
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        self._grid.setSpacing(ResultCard.CARD_SPACING)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Style
        self.setStyleSheet(f"""
            QScrollArea#cardsScrollArea {{
                background-color: {COLORS['background']};
                border: none;
            }}
            QWidget#cardsContainer {{
                background-color: {COLORS['background']};
            }}
        """)

    def set_data(self, data: List[Dict[str, Any]]) -> None:
        """
        Set the data to display.

        Args:
            data: List of item data dictionaries
        """
        self._data = data
        self._selected_indices.clear()
        self._rebuild_cards()

    def _rebuild_cards(self) -> None:
        """Rebuild all cards from data."""
        # Clear existing cards
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        # Clear grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Calculate columns based on width
        available_width = self.viewport().width() - (Spacing.MD * 2)
        card_total_width = ResultCard.CARD_WIDTH + ResultCard.CARD_SPACING
        columns = max(
            self.MIN_COLUMNS,
            min(self.MAX_COLUMNS, available_width // card_total_width)
        )

        # Create cards
        for i, item_data in enumerate(self._data):
            card = ResultCard(item_data, self._container)
            card.clicked.connect(lambda d, idx=i: self._on_card_clicked(idx, d))
            card.double_clicked.connect(self.card_double_clicked.emit)
            card.context_menu_requested.connect(self._show_context_menu)

            row = i // columns
            col = i % columns
            self._grid.addWidget(card, row, col)
            self._cards.append(card)

    def _on_card_clicked(self, index: int, data: Dict[str, Any]) -> None:
        """Handle card click with selection logic."""
        modifiers = QApplication.keyboardModifiers()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Toggle selection
            if index in self._selected_indices:
                self._selected_indices.remove(index)
                self._cards[index].set_selected(False)
            else:
                self._selected_indices.add(index)
                self._cards[index].set_selected(True)
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Range selection
            if self._selected_indices:
                last = max(self._selected_indices)
                start, end = min(last, index), max(last, index)
                for i in range(start, end + 1):
                    self._selected_indices.add(i)
                    self._cards[i].set_selected(True)
            else:
                self._selected_indices.add(index)
                self._cards[index].set_selected(True)
        else:
            # Single selection
            for i, card in enumerate(self._cards):
                card.set_selected(i == index)
            self._selected_indices = {index}

        # Emit signals
        self.card_clicked.emit(data)
        self.cards_selected.emit(self.get_selected_data())

    def _show_context_menu(self, data: Dict[str, Any], pos: QPoint) -> None:
        """Show context menu for card."""
        selected = self.get_selected_data()
        if not selected:
            selected = [data]

        menu = QMenu(self)
        count = len(selected)

        # Single item actions
        if count == 1:
            inspect_action = menu.addAction("Inspect Item")
            inspect_action.triggered.connect(
                lambda: self.card_double_clicked.emit(selected[0])
            )

        # Multi-item actions
        if count >= 2:
            compare_action = menu.addAction(f"Compare {count} Items")
            compare_action.triggered.connect(
                lambda: self.compare_requested.emit(selected)
            )
            if count > 3:
                compare_action.setEnabled(False)
                compare_action.setText("Compare Items (max 3)")

        menu.addSeparator()

        # Copy actions
        copy_menu = menu.addMenu("Copy")
        copy_names = copy_menu.addAction("Item Names")
        copy_names.triggered.connect(
            lambda: self._copy_to_clipboard(
                [r.get("item_name", "") for r in selected]
            )
        )
        copy_prices = copy_menu.addAction("Prices (Chaos)")
        copy_prices.triggered.connect(
            lambda: self._copy_to_clipboard(
                [str(r.get("chaos_value", "")) for r in selected]
            )
        )

        menu.addSeparator()

        # Export
        export_action = menu.addAction(f"Export {count} Item(s)...")
        export_action.triggered.connect(
            lambda: self.export_requested.emit(selected)
        )

        # Select all
        menu.addSeparator()
        select_all = menu.addAction("Select All")
        select_all.triggered.connect(self.select_all)

        menu.exec(pos)

    def _copy_to_clipboard(self, items: List[str]) -> None:
        """Copy items to clipboard."""
        text = "\n".join(str(item) for item in items if item)
        QApplication.clipboard().setText(text)

    def get_selected_data(self) -> List[Dict[str, Any]]:
        """Get data for all selected cards."""
        return [self._data[i] for i in sorted(self._selected_indices)]

    def get_selected_count(self) -> int:
        """Get number of selected cards."""
        return len(self._selected_indices)

    def select_all(self) -> None:
        """Select all cards."""
        self._selected_indices = set(range(len(self._cards)))
        for card in self._cards:
            card.set_selected(True)
        self.cards_selected.emit(self.get_selected_data())

    def clear_selection(self) -> None:
        """Clear all selection."""
        self._selected_indices.clear()
        for card in self._cards:
            card.set_selected(False)
        self.cards_selected.emit([])

    def resizeEvent(self, event) -> None:
        """Handle resize to reflow cards."""
        super().resizeEvent(event)
        # Rebuild cards on resize to adjust columns
        if self._data:
            QTimer.singleShot(0, self._rebuild_cards)
