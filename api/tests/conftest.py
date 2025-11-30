"""
api.tests.conftest - Pytest fixtures for API tests.

Provides test client and mock dependencies for testing API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_database() -> MagicMock:
    """Create a mock database with standard test data."""
    db = MagicMock()

    # Mock checked items
    mock_items = [
        MagicMock(
            id=1,
            game_version="poe1",
            league="Standard",
            item_name="Headhunter",
            chaos_value=15000.0,
            divine_value=85.0,
            rarity="unique",
            checked_at=datetime(2025, 11, 30, 12, 0, 0),
        ),
        MagicMock(
            id=2,
            game_version="poe1",
            league="Standard",
            item_name="Chaos Orb",
            chaos_value=1.0,
            divine_value=None,
            rarity="currency",
            checked_at=datetime(2025, 11, 30, 11, 0, 0),
        ),
    ]
    db.get_checked_items.return_value = mock_items

    # Mock sales
    mock_sales = [
        MagicMock(
            id=1,
            item_name="Tabula Rasa",
            listed_price_chaos=10.0,
            actual_price_chaos=12.0,
            listed_at=datetime(2025, 11, 29, 10, 0, 0),
            sold_at=datetime(2025, 11, 29, 12, 0, 0),
            time_to_sale_hours=2.0,
            notes="Quick sale",
        ),
        MagicMock(
            id=2,
            item_name="Goldrim",
            listed_price_chaos=5.0,
            actual_price_chaos=None,
            listed_at=datetime(2025, 11, 30, 10, 0, 0),
            sold_at=None,
            time_to_sale_hours=None,
            notes=None,
        ),
    ]
    db.get_sales.return_value = mock_sales

    # Mock record methods
    db.record_sale.return_value = 3
    db.record_instant_sale.return_value = 4
    db.add_checked_item.return_value = 3

    return db


@pytest.fixture
def mock_price_service() -> MagicMock:
    """Create a mock price service."""
    service = MagicMock()

    # Mock price result
    mock_result = MagicMock()
    mock_result.prices = {
        "poe.ninja": {"chaos": 15000.0, "divine": 85.0, "count": 42},
        "poe.watch": {"chaos": 14800.0, "divine": 84.0, "count": 38},
    }
    mock_result.explanation = "Unique belt with high demand"

    service.check_item.return_value = mock_result
    return service


@pytest.fixture
def mock_item_parser() -> MagicMock:
    """Create a mock item parser."""
    parser = MagicMock()

    # Mock parsed item
    mock_item = MagicMock()
    mock_item.name = "Headhunter"
    mock_item.base_type = "Leather Belt"
    mock_item.rarity = MagicMock(value="unique")
    mock_item.item_level = 86
    mock_item.mods = ["When you Kill a Rare Monster, you gain its Modifiers for 20 seconds"]
    mock_item.sockets = None
    mock_item.corrupted = False
    mock_item.influences = []

    parser.parse.return_value = mock_item
    return parser


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock config."""
    config = MagicMock()
    config.league = "Standard"
    config.game_version = MagicMock(value="poe1")
    config.auto_detect_league = True
    config.cache_ttl_seconds = 3600
    return config


@pytest.fixture
def mock_app_context(
    mock_database: MagicMock,
    mock_price_service: MagicMock,
    mock_item_parser: MagicMock,
    mock_config: MagicMock,
) -> MagicMock:
    """Create a mock app context with all services."""
    ctx = MagicMock()
    ctx.database = mock_database
    ctx.price_service = mock_price_service
    ctx.item_parser = mock_item_parser
    ctx.config = mock_config
    ctx.close = MagicMock()
    return ctx


@pytest.fixture
def client(mock_app_context: MagicMock) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""
    # Import here to avoid circular imports
    from api.main import app
    from api import dependencies

    # Override the get_app_context function in dependencies module
    original_get_ctx = dependencies.get_app_context

    def mock_get_ctx():
        return mock_app_context

    dependencies.get_app_context = mock_get_ctx

    # Also patch the global context in main
    import api.main
    original_context = api.main._app_context
    api.main._app_context = mock_app_context

    # Override in FastAPI dependency system
    app.dependency_overrides[original_get_ctx] = mock_get_ctx

    with TestClient(app) as test_client:
        yield test_client

    # Restore
    dependencies.get_app_context = original_get_ctx
    api.main._app_context = original_context
    app.dependency_overrides.clear()
