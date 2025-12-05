"""
Virtual Scroll - Virtual scrolling for large lists.

Provides efficient scrolling for lists with thousands of items
by only rendering visible rows and recycling row widgets.

Usage:
    from gui_qt.performance.virtual_scroll import (
        VirtualScrollArea,
        VirtualListModel,
        RowDelegate,
    )

    # Create model with data
    model = VirtualListModel(data_list)

    # Create delegate for row rendering
    class MyDelegate(RowDelegate):
        def create_widget(self) -> QWidget:
            return MyRowWidget()

        def bind(self, widget: QWidget, data: Any) -> None:
            widget.set_data(data)

    # Create virtual scroll area
    scroll = VirtualScrollArea()
    scroll.set_model(model)
    scroll.set_delegate(MyDelegate())
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Generic, List, Optional, TypeVar

from PyQt6.QtCore import Qt, QObject, QTimer, QRect, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QScrollArea,
    QVBoxLayout,
    QFrame,
    QSizePolicy,
)

logger = logging.getLogger(__name__)


T = TypeVar('T')


class VirtualListModel(Generic[T]):
    """
    Model for virtual list data.

    Provides data access and change notifications
    for virtual scrolling.
    """

    def __init__(self, data: Optional[List[T]] = None):
        """
        Initialize model with data.

        Args:
            data: Initial data list
        """
        self._data: List[T] = data or []
        self._on_change_callbacks: List[callable] = []

    def set_data(self, data: List[T]) -> None:
        """
        Set new data and notify listeners.

        Args:
            data: New data list
        """
        self._data = data
        self._notify_change()

    def append(self, item: T) -> None:
        """
        Append item to data.

        Args:
            item: Item to append
        """
        self._data.append(item)
        self._notify_change()

    def remove(self, index: int) -> None:
        """
        Remove item at index.

        Args:
            index: Index to remove
        """
        if 0 <= index < len(self._data):
            del self._data[index]
            self._notify_change()

    def get(self, index: int) -> Optional[T]:
        """
        Get item at index.

        Args:
            index: Item index

        Returns:
            Item or None if out of bounds
        """
        if 0 <= index < len(self._data):
            return self._data[index]
        return None

    def count(self) -> int:
        """Get item count."""
        return len(self._data)

    def on_change(self, callback: callable) -> None:
        """
        Register change callback.

        Args:
            callback: Function to call on data change
        """
        self._on_change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify all change listeners."""
        for callback in self._on_change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Change callback error: {e}")


class RowDelegate(ABC):
    """
    Abstract delegate for row widget creation and binding.

    Implement this to define how rows are rendered.
    """

    @abstractmethod
    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """
        Create a new row widget.

        Args:
            parent: Parent widget

        Returns:
            New row widget (will be recycled)
        """
        pass

    @abstractmethod
    def bind(self, widget: QWidget, data: Any, index: int) -> None:
        """
        Bind data to a row widget.

        Args:
            widget: Row widget to update
            data: Data for this row
            index: Row index
        """
        pass

    def row_height(self) -> int:
        """
        Get fixed row height.

        Returns:
            Row height in pixels (0 for variable height)
        """
        return 40  # Default fixed height

    def unbind(self, widget: QWidget) -> None:
        """
        Called when widget is recycled.

        Override to clean up bindings.

        Args:
            widget: Widget being recycled
        """
        pass


class SimpleRowDelegate(RowDelegate):
    """
    Simple delegate using a label for each row.

    Useful for basic text lists.
    """

    def __init__(self, row_height: int = 40):
        """
        Initialize simple delegate.

        Args:
            row_height: Fixed row height
        """
        from PyQt6.QtWidgets import QLabel

        self._row_height = row_height

    def create_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create a label widget."""
        from PyQt6.QtWidgets import QLabel

        label = QLabel(parent)
        label.setStyleSheet("padding: 8px;")
        return label

    def bind(self, widget: QWidget, data: Any, index: int) -> None:
        """Bind data to label."""
        widget.setText(str(data))

    def row_height(self) -> int:
        """Get row height."""
        return self._row_height


class VirtualScrollArea(QScrollArea):
    """
    Virtual scrolling area for large lists.

    Only renders visible rows and recycles row widgets
    for efficient memory usage.
    """

    # Emitted when a row is clicked
    row_clicked = pyqtSignal(int, object)  # index, data

    # Emitted when a row is double-clicked
    row_double_clicked = pyqtSignal(int, object)  # index, data

    # Emitted when selection changes
    selection_changed = pyqtSignal(list)  # list of indices

    # Buffer rows above/below visible area
    BUFFER_ROWS = 5

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize virtual scroll area."""
        super().__init__(parent)

        self._model: Optional[VirtualListModel] = None
        self._delegate: Optional[RowDelegate] = None

        # Row widget pool for recycling
        self._widget_pool: List[QWidget] = []
        self._active_widgets: Dict[int, QWidget] = {}  # index -> widget

        # Visible range
        self._first_visible = 0
        self._last_visible = -1

        # Selection
        self._selected_indices: set = set()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the scroll area."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container widget
        self._container = QWidget()
        self._container.setObjectName("virtualScrollContainer")
        self.setWidget(self._container)

        # Connect scroll events
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def set_model(self, model: VirtualListModel) -> None:
        """
        Set the data model.

        Args:
            model: Virtual list model
        """
        self._model = model
        model.on_change(self._on_model_changed)
        self._update_container_size()
        self._update_visible_rows()

    def set_delegate(self, delegate: RowDelegate) -> None:
        """
        Set the row delegate.

        Args:
            delegate: Row delegate
        """
        self._delegate = delegate
        self._clear_widgets()
        self._update_visible_rows()

    def _update_container_size(self) -> None:
        """Update container to reflect total content height."""
        if not self._model or not self._delegate:
            return

        total_height = self._model.count() * self._delegate.row_height()
        self._container.setFixedHeight(total_height)

    def _on_model_changed(self) -> None:
        """Handle model data change."""
        self._update_container_size()
        self._update_visible_rows()

    def _on_scroll(self, value: int) -> None:
        """Handle scroll event."""
        self._update_visible_rows()

    def _update_visible_rows(self) -> None:
        """Update which rows are rendered."""
        if not self._model or not self._delegate:
            return

        row_height = self._delegate.row_height()
        if row_height <= 0:
            return

        # Calculate visible range
        viewport_height = self.viewport().height()
        scroll_y = self.verticalScrollBar().value()

        first = max(0, scroll_y // row_height - self.BUFFER_ROWS)
        last = min(
            self._model.count() - 1,
            (scroll_y + viewport_height) // row_height + self.BUFFER_ROWS
        )

        # Check if range changed
        if first == self._first_visible and last == self._last_visible:
            return

        self._first_visible = first
        self._last_visible = last

        # Recycle widgets outside range
        indices_to_remove = [
            i for i in self._active_widgets
            if i < first or i > last
        ]
        for index in indices_to_remove:
            self._recycle_widget(index)

        # Create/reuse widgets for visible range
        for index in range(first, last + 1):
            if index not in self._active_widgets:
                self._show_row(index)

    def _show_row(self, index: int) -> None:
        """Show a row at the given index."""
        widget = self._get_widget()
        data = self._model.get(index)

        if data is not None:
            self._delegate.bind(widget, data, index)

        # Position widget
        row_height = self._delegate.row_height()
        widget.setParent(self._container)
        widget.setGeometry(0, index * row_height, self._container.width(), row_height)
        widget.show()

        # Track
        self._active_widgets[index] = widget

        # Update selection state
        widget.setProperty("selected", index in self._selected_indices)
        self._update_widget_style(widget)

    def _get_widget(self) -> QWidget:
        """Get a widget from pool or create new."""
        if self._widget_pool:
            return self._widget_pool.pop()

        widget = self._delegate.create_widget(self._container)
        widget.mousePressEvent = lambda e, w=widget: self._on_widget_click(w, e)
        widget.mouseDoubleClickEvent = lambda e, w=widget: self._on_widget_double_click(w, e)
        return widget

    def _recycle_widget(self, index: int) -> None:
        """Recycle widget at index back to pool."""
        if index in self._active_widgets:
            widget = self._active_widgets.pop(index)
            self._delegate.unbind(widget)
            widget.hide()
            self._widget_pool.append(widget)

    def _clear_widgets(self) -> None:
        """Clear all active widgets."""
        for index in list(self._active_widgets.keys()):
            self._recycle_widget(index)
        self._first_visible = 0
        self._last_visible = -1

    def _on_widget_click(self, widget: QWidget, event) -> None:
        """Handle widget click."""
        index = self._get_widget_index(widget)
        if index is None:
            return

        data = self._model.get(index)

        # Handle selection
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Toggle selection
            if index in self._selected_indices:
                self._selected_indices.remove(index)
            else:
                self._selected_indices.add(index)
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Range selection
            if self._selected_indices:
                last = max(self._selected_indices)
                start, end = min(last, index), max(last, index)
                for i in range(start, end + 1):
                    self._selected_indices.add(i)
            else:
                self._selected_indices.add(index)
        else:
            # Single selection
            self._selected_indices = {index}

        # Update widget styles
        for i, w in self._active_widgets.items():
            w.setProperty("selected", i in self._selected_indices)
            self._update_widget_style(w)

        self.row_clicked.emit(index, data)
        self.selection_changed.emit(list(self._selected_indices))

    def _on_widget_double_click(self, widget: QWidget, event) -> None:
        """Handle widget double-click."""
        index = self._get_widget_index(widget)
        if index is not None:
            data = self._model.get(index)
            self.row_double_clicked.emit(index, data)

    def _get_widget_index(self, widget: QWidget) -> Optional[int]:
        """Get index for a widget."""
        for index, w in self._active_widgets.items():
            if w is widget:
                return index
        return None

    def _update_widget_style(self, widget: QWidget) -> None:
        """Update widget style based on selection."""
        selected = widget.property("selected")
        if selected:
            widget.setStyleSheet("background-color: #3d5a80;")
        else:
            widget.setStyleSheet("")

    def get_selected_indices(self) -> List[int]:
        """Get list of selected indices."""
        return sorted(self._selected_indices)

    def get_selected_data(self) -> List[Any]:
        """Get data for selected rows."""
        return [
            self._model.get(i)
            for i in sorted(self._selected_indices)
            if self._model.get(i) is not None
        ]

    def select_all(self) -> None:
        """Select all rows."""
        if self._model:
            self._selected_indices = set(range(self._model.count()))
            for i, w in self._active_widgets.items():
                w.setProperty("selected", True)
                self._update_widget_style(w)
            self.selection_changed.emit(list(self._selected_indices))

    def clear_selection(self) -> None:
        """Clear selection."""
        self._selected_indices.clear()
        for w in self._active_widgets.values():
            w.setProperty("selected", False)
            self._update_widget_style(w)
        self.selection_changed.emit([])

    def scroll_to_index(self, index: int) -> None:
        """
        Scroll to make an index visible.

        Args:
            index: Row index to scroll to
        """
        if not self._delegate:
            return

        row_height = self._delegate.row_height()
        target_y = index * row_height
        self.verticalScrollBar().setValue(target_y)

    def resizeEvent(self, event) -> None:
        """Handle resize to update visible rows."""
        super().resizeEvent(event)
        # Update widget widths
        for widget in self._active_widgets.values():
            widget.setFixedWidth(self._container.width())
        self._update_visible_rows()
