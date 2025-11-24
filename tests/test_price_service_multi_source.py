"""
Test PriceService with poe.watch integration.
"""

import pytest
from unittest.mock import Mock, MagicMock
from core.price_service import PriceService
from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from core.game_version import GameVersion
from data_sources.pricing.poe_ninja import PoeNinjaAPI
from data_sources.pricing.poe_watch import PoeWatchAPI


@pytest.fixture
def mock_config():
    config = Mock(spec=Config)
    config.current_game = GameVersion.POE1
    config.get_game_config = Mock()
    config.get_game_config.return_value = Mock(league="Standard")
    return config


@pytest.fixture
def mock_parser():
    return Mock(spec=ItemParser)


@pytest.fixture
def mock_database():
    return Mock(spec=Database)


@pytest.fixture
def mock_poe_ninja():
    ninja = Mock(spec=PoeNinjaAPI)
    ninja.league = "Standard"
    ninja.divine_chaos_rate = 200.0
    ninja.ensure_divine_rate = Mock(return_value=200.0)
    return ninja


@pytest.fixture
def mock_poe_watch():
    watch = Mock(spec=PoeWatchAPI)
    watch.league = "Standard"
    return watch


def test_price_service_init_with_poe_watch(
    mock_config,
    mock_parser,
    mock_database,
    mock_poe_ninja,
    mock_poe_watch
):
    """Test that PriceService can be initialized with poe.watch."""
    service = PriceService(
        config=mock_config,
        parser=mock_parser,
        db=mock_database,
        poe_ninja=mock_poe_ninja,
        poe_watch=mock_poe_watch
    )
    
    assert service.poe_watch is not None
    assert service.poe_ninja is not None


def test_multi_source_both_agree(
    mock_config,
    mock_parser,
    mock_database,
    mock_poe_ninja,
    mock_poe_watch
):
    """Test when both sources agree on price."""
    service = PriceService(
        config=mock_config,
        parser=mock_parser,
        db=mock_database,
        poe_ninja=mock_poe_ninja,
        poe_watch=mock_poe_watch
    )
    
    # Create mock parsed item
    parsed = Mock()
    parsed.display_name = "Divine Orb"
    parsed.name = "Divine Orb"
    parsed.rarity = "CURRENCY"
    parsed.base_type = None
    parsed.gem_level = None
    parsed.gem_quality = None
    parsed.corrupted = None
    parsed.links = 0
    
    # Mock poe.ninja response (100 chaos)
    mock_poe_ninja.get_currency_overview = Mock(return_value={
        'lines': [{
            'currencyTypeName': 'Divine Orb',
            'chaosEquivalent': 100.0
        }]
    })
    
    # Mock poe.watch response (105 chaos - within 20%)
    mock_poe_watch.find_item_price = Mock(return_value={
        'mean': 105.0,
        'daily': 50,
        'lowConfidence': False
    })
    
    chaos, count, source, confidence = service._lookup_price_multi_source(parsed)
    
    # Should use ninja price (faster updates) with high confidence
    assert chaos == 100.0
    assert "validated" in source.lower()
    assert confidence == "high"


def test_multi_source_divergence(
    mock_config,
    mock_parser,
    mock_database,
    mock_poe_ninja,
    mock_poe_watch
):
    """Test when sources disagree significantly."""
    service = PriceService(
        config=mock_config,
        parser=mock_parser,
        db=mock_database,
        poe_ninja=mock_poe_ninja,
        poe_watch=mock_poe_watch
    )
    
    parsed = Mock()
    parsed.display_name = "Headhunter"
    parsed.name = "Headhunter"
    parsed.rarity = "UNIQUE"
    parsed.base_type = "Leather Belt"
    parsed.gem_level = None
    parsed.gem_quality = None
    parsed.corrupted = False
    parsed.links = 0
    
    # Mock ninja: 100 divines (20000 chaos)
    mock_poe_ninja.find_item_price = Mock(return_value={
        'chaosValue': 20000.0,
        'count': 10
    })
    
    # Mock watch: 150 divines (30000 chaos) - 50% difference!
    mock_poe_watch.find_item_price = Mock(return_value={
        'mean': 30000.0,
        'daily': 5,
        'lowConfidence': False
    })
    
    chaos, count, source, confidence = service._lookup_price_multi_source(parsed)
    
    # Should average: (20000 + 30000) / 2 = 25000
    assert chaos == 25000.0
    assert "averaged" in source.lower()
    assert confidence == "medium"


def test_multi_source_watch_low_confidence(
    mock_config,
    mock_parser,
    mock_database,
    mock_poe_ninja,
    mock_poe_watch
):
    """Test when poe.watch flags low confidence."""
    service = PriceService(
        config=mock_config,
        parser=mock_parser,
        db=mock_database,
        poe_ninja=mock_poe_ninja,
        poe_watch=mock_poe_watch
    )
    
    parsed = Mock()
    parsed.display_name = "Rare Item"
    parsed.name = "Rare Item"
    parsed.rarity = "UNIQUE"
    parsed.base_type = "Ring"
    parsed.gem_level = None
    parsed.gem_quality = None
    parsed.corrupted = None
    parsed.links = 0
    
    # Mock ninja: 50 chaos
    mock_poe_ninja.find_item_price = Mock(return_value={
        'chaosValue': 50.0,
        'count': 20
    })
    
    # Mock watch: 100 chaos but LOW CONFIDENCE
    mock_poe_watch.find_item_price = Mock(return_value={
        'mean': 100.0,
        'daily': 2,
        'lowConfidence': True  # Flagged as unreliable
    })
    
    chaos, count, source, confidence = service._lookup_price_multi_source(parsed)
    
    # Should prefer ninja when watch has low confidence
    assert chaos == 50.0
    assert "ninja" in source.lower()
    assert "low confidence" in source.lower()
    assert confidence == "medium"


def test_multi_source_only_ninja(
    mock_config,
    mock_parser,
    mock_database,
    mock_poe_ninja,
    mock_poe_watch
):
    """Test when only poe.ninja has data."""
    service = PriceService(
        config=mock_config,
        parser=mock_parser,
        db=mock_database,
        poe_ninja=mock_poe_ninja,
        poe_watch=mock_poe_watch
    )
    
    parsed = Mock()
    parsed.display_name = "Item"
    parsed.name = "Item"
    parsed.rarity = "UNIQUE"
    parsed.base_type = None
    parsed.gem_level = None
    parsed.gem_quality = None
    parsed.corrupted = None
    parsed.links = 0
    
    # Mock ninja has data
    mock_poe_ninja.find_item_price = Mock(return_value={
        'chaosValue': 75.0,
        'count': 15
    })
    
    # Mock watch has no data
    mock_poe_watch.find_item_price = Mock(return_value=None)
    
    chaos, count, source, confidence = service._lookup_price_multi_source(parsed)
    
    assert chaos == 75.0
    assert "ninja only" in source.lower()
    assert confidence == "medium"


def test_multi_source_only_watch(
    mock_config,
    mock_parser,
    mock_database,
    mock_poe_ninja,
    mock_poe_watch
):
    """Test when only poe.watch has data."""
    service = PriceService(
        config=mock_config,
        parser=mock_parser,
        db=mock_database,
        poe_ninja=mock_poe_ninja,
        poe_watch=mock_poe_watch
    )
    
    parsed = Mock()
    parsed.display_name = "Item"
    parsed.name = "Item"
    parsed.rarity = "UNIQUE"
    parsed.base_type = None
    parsed.gem_level = None
    parsed.gem_quality = None
    parsed.corrupted = None
    parsed.links = 0
    
    # Mock ninja has no data
    mock_poe_ninja.find_item_price = Mock(return_value=None)
    
    # Mock watch has data
    mock_poe_watch.find_item_price = Mock(return_value={
        'mean': 125.0,
        'daily': 30,
        'lowConfidence': False
    })
    
    chaos, count, source, confidence = service._lookup_price_multi_source(parsed)
    
    assert chaos == 125.0
    assert "watch only" in source.lower()
    assert confidence == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
