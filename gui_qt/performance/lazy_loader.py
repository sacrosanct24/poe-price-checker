"""
Lazy Loader - Lazy widget initialization and progressive loading.

Provides utilities for deferring expensive widget initialization
until the widget is actually needed, improving startup time.

Usage:
    from gui_qt.performance.lazy_loader import (
        LazyLoader,
        LazyWidget,
        lazy_property,
    )

    # Create a lazy widget
    class ExpensiveWidget(QWidget):
        pass

    lazy = LazyWidget(ExpensiveWidget, arg1, arg2, kwarg=value)
    # Widget not created yet

    # Access triggers creation
    widget = lazy.widget()

    # Or use lazy_property decorator
    class MyWindow(QMainWindow):
        @lazy_property
        def expensive_panel(self) -> ExpensivePanel:
            return ExpensivePanel(self)
"""

from functools import wraps
import logging
from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar
from weakref import WeakValueDictionary

from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout

logger = logging.getLogger(__name__)


T = TypeVar('T')
W = TypeVar('W', bound=QWidget)


class LazyWidget(Generic[W]):
    """
    Lazy wrapper for widget creation.

    Defers widget instantiation until first access, reducing startup overhead.
    """

    def __init__(
        self,
        widget_class: Type[W],
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize lazy widget wrapper.

        Args:
            widget_class: The widget class to instantiate
            *args: Positional arguments for widget constructor
            **kwargs: Keyword arguments for widget constructor
        """
        self._widget_class = widget_class
        self._args = args
        self._kwargs = kwargs
        self._widget: Optional[W] = None
        self._initialized = False

    def widget(self) -> W:
        """
        Get the widget, creating it if necessary.

        Returns:
            The widget instance
        """
        if self._widget is None:
            logger.debug(f"Lazy-loading {self._widget_class.__name__}")
            self._widget = self._widget_class(*self._args, **self._kwargs)
            self._initialized = True
        return self._widget

    def is_initialized(self) -> bool:
        """Check if widget has been created."""
        return self._initialized

    def __call__(self) -> W:
        """Shorthand for widget()."""
        return self.widget()


def lazy_property(func: Callable[[Any], T]) -> property:
    """
    Decorator for lazy property initialization.

    The property value is computed on first access and cached.

    Usage:
        class MyWindow(QMainWindow):
            @lazy_property
            def expensive_panel(self) -> ExpensivePanel:
                return ExpensivePanel(self)
    """
    attr_name = f"_lazy_{func.__name__}"

    @wraps(func)
    def wrapper(self: Any) -> T:
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)

    return property(wrapper)


def defer_initialization(
    delay_ms: int = 0,
) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """
    Decorator to defer method execution until after event loop starts.

    Useful for deferring non-critical initialization that would slow startup.

    Args:
        delay_ms: Delay in milliseconds (0 = next event loop iteration)

    Usage:
        class MyWindow(QMainWindow):
            @defer_initialization(100)
            def _load_cached_data(self) -> None:
                # This runs 100ms after construction
                self._cache = load_data()
    """
    def decorator(func: Callable[..., None]) -> Callable[..., None]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
            QTimer.singleShot(
                delay_ms,
                lambda: func(self, *args, **kwargs)
            )
        return wrapper
    return decorator


class LazyLoader(QObject):
    """
    Manager for lazy loading multiple components.

    Tracks and manages lazy-loaded widgets with priorities
    and progressive loading support.
    """

    # Emitted when a widget is loaded
    widget_loaded = pyqtSignal(str)  # widget key

    # Emitted when all queued widgets are loaded
    loading_complete = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize lazy loader."""
        super().__init__(parent)

        self._pending: Dict[str, tuple] = {}  # key -> (factory, priority)
        self._loaded: Dict[str, QWidget] = {}
        self._loading = False
        self._timer: Optional[QTimer] = None

    def register(
        self,
        key: str,
        factory: Callable[[], QWidget],
        *,
        priority: int = 0,
        preload: bool = False,
    ) -> None:
        """
        Register a widget for lazy loading.

        Args:
            key: Unique identifier for the widget
            factory: Function that creates the widget
            priority: Loading priority (higher = sooner)
            preload: If True, load immediately in background
        """
        if key in self._loaded:
            return

        self._pending[key] = (factory, priority)

        if preload:
            self._queue_load(key)

    def get(self, key: str) -> Optional[QWidget]:
        """
        Get a registered widget, loading it if necessary.

        Args:
            key: Widget identifier

        Returns:
            The widget, or None if not registered
        """
        # Already loaded
        if key in self._loaded:
            return self._loaded[key]

        # Pending - load now
        if key in self._pending:
            return self._load_widget(key)

        return None

    def is_loaded(self, key: str) -> bool:
        """Check if a widget is loaded."""
        return key in self._loaded

    def preload_all(self, interval_ms: int = 50) -> None:
        """
        Progressively load all pending widgets.

        Args:
            interval_ms: Interval between widget loads
        """
        if self._loading or not self._pending:
            return

        self._loading = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load_next)
        self._timer.start(interval_ms)

    def _load_widget(self, key: str) -> QWidget:
        """Load a specific widget."""
        if key not in self._pending:
            raise ValueError(f"Widget '{key}' not registered")

        factory, _ = self._pending.pop(key)

        try:
            logger.debug(f"Loading widget: {key}")
            widget = factory()
            self._loaded[key] = widget
            self.widget_loaded.emit(key)
            return widget
        except Exception as e:
            logger.error(f"Failed to load widget '{key}': {e}")
            raise

    def _queue_load(self, key: str) -> None:
        """Queue a widget for background loading."""
        QTimer.singleShot(0, lambda: self._load_widget(key))

    def _load_next(self) -> None:
        """Load the next pending widget."""
        if not self._pending:
            self._loading = False
            if self._timer:
                self._timer.stop()
                self._timer = None
            self.loading_complete.emit()
            return

        # Get highest priority
        key = max(self._pending.keys(), key=lambda k: self._pending[k][1])
        self._load_widget(key)

    def unload(self, key: str) -> None:
        """
        Unload a widget to free memory.

        Args:
            key: Widget identifier
        """
        if key in self._loaded:
            widget = self._loaded.pop(key)
            widget.deleteLater()
            logger.debug(f"Unloaded widget: {key}")


class LazyStackedWidget(QStackedWidget):
    """
    Stacked widget that lazy-loads pages on first access.

    Pages are only created when first shown, reducing memory
    and startup time for complex multi-page UIs.
    """

    page_loaded = pyqtSignal(int, QWidget)  # index, widget

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize lazy stacked widget."""
        super().__init__(parent)

        self._factories: Dict[int, Callable[[], QWidget]] = {}
        self._placeholders: Dict[int, QWidget] = {}

    def add_lazy_page(
        self,
        factory: Callable[[], QWidget],
        *,
        placeholder: Optional[QWidget] = None,
    ) -> int:
        """
        Add a lazy-loaded page.

        Args:
            factory: Function that creates the page widget
            placeholder: Optional placeholder widget while loading

        Returns:
            The page index
        """
        # Create placeholder if not provided
        if placeholder is None:
            placeholder = QWidget()

        index = self.addWidget(placeholder)
        self._factories[index] = factory
        self._placeholders[index] = placeholder

        return index

    def setCurrentIndex(self, index: int) -> None:
        """
        Switch to a page, loading it if necessary.

        Args:
            index: Page index
        """
        # Load if still using placeholder
        if index in self._factories:
            self._load_page(index)

        super().setCurrentIndex(index)

    def _load_page(self, index: int) -> QWidget:
        """Load a lazy page."""
        factory = self._factories.pop(index)
        placeholder = self._placeholders.pop(index)

        # Create real widget
        widget = factory()

        # Replace placeholder
        self.removeWidget(placeholder)
        placeholder.deleteLater()
        self.insertWidget(index, widget)

        self.page_loaded.emit(index, widget)
        logger.debug(f"Loaded page at index {index}")

        return widget

    def widget_at(self, index: int) -> Optional[QWidget]:
        """
        Get widget at index, loading if necessary.

        Args:
            index: Page index

        Returns:
            The widget
        """
        if index in self._factories:
            return self._load_page(index)
        return self.widget(index)

    def is_loaded(self, index: int) -> bool:
        """Check if a page is loaded."""
        return index not in self._factories


class BatchProcessor(QObject):
    """
    Process items in batches to keep UI responsive.

    Splits large operations into smaller chunks with
    yields to the event loop between batches.
    """

    # Emitted after each batch
    batch_complete = pyqtSignal(int, int)  # processed, total

    # Emitted when all processing is done
    processing_complete = pyqtSignal()

    def __init__(
        self,
        batch_size: int = 50,
        interval_ms: int = 10,
        parent: Optional[QObject] = None,
    ):
        """
        Initialize batch processor.

        Args:
            batch_size: Items to process per batch
            interval_ms: Delay between batches
            parent: Parent object
        """
        super().__init__(parent)

        self._batch_size = batch_size
        self._interval_ms = interval_ms
        self._items: list = []
        self._processor: Optional[Callable] = None
        self._processed = 0
        self._timer: Optional[QTimer] = None

    def process(
        self,
        items: list,
        processor: Callable[[Any], Any],
    ) -> None:
        """
        Start batch processing items.

        Args:
            items: Items to process
            processor: Function to call for each item
        """
        self._items = list(items)
        self._processor = processor
        self._processed = 0

        if not self._items:
            self.processing_complete.emit()
            return

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_batch)
        self._timer.start(self._interval_ms)

    def _process_batch(self) -> None:
        """Process one batch of items."""
        if not self._items:
            self._complete()
            return

        # Process batch
        batch = self._items[:self._batch_size]
        self._items = self._items[self._batch_size:]

        for item in batch:
            if self._processor:
                self._processor(item)
            self._processed += 1

        self.batch_complete.emit(self._processed, self._processed + len(self._items))

        if not self._items:
            self._complete()

    def _complete(self) -> None:
        """Complete processing."""
        if self._timer:
            self._timer.stop()
            self._timer = None
        self.processing_complete.emit()

    def cancel(self) -> None:
        """Cancel processing."""
        self._items.clear()
        if self._timer:
            self._timer.stop()
            self._timer = None
