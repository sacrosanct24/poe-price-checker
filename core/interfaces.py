"""
Service interfaces for dependency injection.

Provides Protocol definitions for core services to avoid circular imports
when modules need type hints for AppContext or its services.

Usage:
    # Instead of:
    if TYPE_CHECKING:
        from core.app_context import AppContext

    # Use:
    from core.interfaces import IAppContext

    class MyWindow(QMainWindow):
        def __init__(self, ctx: IAppContext):
            self.ctx = ctx

This allows modules to depend on interfaces instead of concrete implementations,
eliminating TYPE_CHECKING blocks and potential circular import issues.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, runtime_checkable


@runtime_checkable
class IPriceService(Protocol):
    """Interface for price checking services.

    Any class implementing check_item() with this signature satisfies the protocol.
    This matches MultiSourcePriceService and PriceService.
    """

    def check_item(self, item_text: str) -> List[Dict[str, Any]]:
        """Check prices for an item.

        Args:
            item_text: Raw item text from PoE.

        Returns:
            List of price result dictionaries.
        """
        ...


@runtime_checkable
class IItemParser(Protocol):
    """Interface for item text parsers."""

    def parse(self, item_text: str) -> Any:
        """Parse item text into a ParsedItem.

        Args:
            item_text: Raw item text from PoE clipboard.

        Returns:
            Parsed item object, or None if parsing failed.
        """
        ...


@runtime_checkable
class IConfig(Protocol):
    """Interface for configuration access.

    Provides access to user settings and game configuration.
    """

    @property
    def current_game(self) -> Any:
        """Get the currently selected game version."""
        ...

    def get_game_config(self, game: Any) -> Any:
        """Get configuration for a specific game version."""
        ...

    @property
    def auto_detect_league(self) -> bool:
        """Whether to auto-detect the current league."""
        ...


@runtime_checkable
class IDatabase(Protocol):
    """Interface for database operations."""

    def close(self) -> None:
        """Close the database connection."""
        ...


@runtime_checkable
class IAppContext(Protocol):
    """Interface for the application context.

    Aggregates all core services needed by GUI components.
    Use this for type hints instead of importing AppContext directly.

    Example:
        def __init__(self, ctx: IAppContext):
            self.ctx = ctx
            # Access services through ctx
            results = ctx.price_service.check_item(item_text)
            parsed = ctx.parser.parse(item_text)
    """

    config: IConfig
    parser: IItemParser
    db: IDatabase
    poe_ninja: Optional[Any]  # PoeNinjaAPI | None
    poe_watch: Optional[Any]  # PoeWatchAPI | None
    price_service: IPriceService

    def close(self) -> None:
        """Clean up all resources held by the context."""
        ...
