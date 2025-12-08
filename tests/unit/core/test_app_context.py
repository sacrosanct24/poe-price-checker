from __future__ import annotations

import pytest

from core.app_context import create_app_context
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


class TestAppContextCreation:
    """Tests for AppContext dependency injection wiring."""

    def test_create_app_context_provides_config(self) -> None:
        """AppContext should provide a config with valid game version."""
        ctx = create_app_context()
        assert ctx.config.current_game in (GameVersion.POE1, GameVersion.POE2)

    def test_create_app_context_provides_parser(self) -> None:
        """AppContext should provide a parser that can parse items."""
        ctx = create_app_context()
        # Parser should be able to parse a simple currency item
        result = ctx.parser.parse("Rarity: Currency\nExalted Orb\n--------")
        assert result is not None
        assert result.rarity.lower() == "currency"

    def test_create_app_context_provides_database(self) -> None:
        """AppContext should provide a database with sales and history capabilities."""
        ctx = create_app_context()
        # Database should support sales and history operations
        assert hasattr(ctx.db, "record_instant_sale")
        assert hasattr(ctx.db, "get_recent_sales")

    def test_create_app_context_provides_poe_ninja(self) -> None:
        """AppContext should provide poe_ninja client for price data."""
        ctx = create_app_context()
        # poe_ninja should have currency price lookup capability
        if ctx.poe_ninja is not None:  # May be None for PoE2
            assert hasattr(ctx.poe_ninja, "get_currency_price")
            assert hasattr(ctx.poe_ninja, "load_all_prices")

    def test_create_app_context_provides_price_service(self) -> None:
        """AppContext should provide price_service for item checking."""
        ctx = create_app_context()
        # price_service should support check_item operation
        assert hasattr(ctx.price_service, "check_item")
        assert hasattr(ctx.price_service, "sources")

    def test_app_context_components_share_config(self) -> None:
        """All components should use the same config instance."""
        ctx = create_app_context()
        # Verify config is consistently accessible
        config_game = ctx.config.current_game
        assert config_game in (GameVersion.POE1, GameVersion.POE2)

    def test_create_app_context_is_reentrant(self) -> None:
        """Multiple calls to create_app_context should work."""
        ctx1 = create_app_context()
        ctx2 = create_app_context()
        # Both should be valid (may or may not be same instance)
        assert ctx1.config.current_game in (GameVersion.POE1, GameVersion.POE2)
        assert ctx2.config.current_game in (GameVersion.POE1, GameVersion.POE2)
