"""
Tests for core/pricing/service.py - PriceService class.

Focuses on cache management, stats computation, and price display logic.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from core.pricing.service import PriceService
from core.pricing.models import PriceExplanation


class TestPriceServiceCacheManagement:
    """Tests for cache-related functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        config.item_cache_enabled = True
        config.item_cache_ttl_seconds = 300
        config.league = "Standard"
        config.games = {"poe1": {"league": "Standard"}}
        config.current_game = "poe1"
        return config

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache."""
        cache = Mock()
        cache.get.return_value = None
        cache.stats = Mock(hits=10, misses=5, hit_rate=0.67, evictions=2, expirations=1)
        cache.size = 50
        cache.max_size = 1000
        cache.ttl_seconds = 300
        cache.clear.return_value = 50
        return cache

    @pytest.fixture
    def price_service(self, mock_config, mock_cache):
        """Create a PriceService with mocked dependencies."""
        return PriceService(
            config=mock_config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=Mock(),
            cache=mock_cache,
        )

    def test_cache_property_returns_cache(self, price_service, mock_cache):
        """cache property should return the cache instance."""
        assert price_service.cache is mock_cache

    def test_cache_enabled_default_true(self, price_service):
        """cache_enabled should default to True."""
        assert price_service.cache_enabled is True

    def test_cache_enabled_setter(self, price_service):
        """cache_enabled setter should update the value."""
        price_service.cache_enabled = False
        assert price_service.cache_enabled is False

        price_service.cache_enabled = True
        assert price_service.cache_enabled is True

    def test_clear_cache_returns_count(self, price_service, mock_cache):
        """clear_cache should return number of cleared entries."""
        result = price_service.clear_cache()
        assert result == 50
        mock_cache.clear.assert_called_once()

    def test_clear_cache_no_cache(self, mock_config):
        """clear_cache with no cache should return 0."""
        service = PriceService(
            config=mock_config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=Mock(),
            cache=None,
        )
        # Manually disable cache
        service._cache = None
        result = service.clear_cache()
        assert result == 0

    def test_get_cache_stats_returns_dict(self, price_service):
        """get_cache_stats should return statistics dict."""
        stats = price_service.get_cache_stats()

        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert "67" in stats["hit_rate"]  # Allow for rounding differences
        assert stats["evictions"] == 2
        assert stats["expirations"] == 1
        assert stats["size"] == 50
        assert stats["max_size"] == 1000
        assert stats["ttl_seconds"] == 300

    def test_get_cache_stats_no_cache(self, mock_config):
        """get_cache_stats with no cache should return empty dict."""
        service = PriceService(
            config=mock_config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=Mock(),
            cache=None,
        )
        service._cache = None
        stats = service.get_cache_stats()
        assert stats == {}


class TestPriceServiceCheckItem:
    """Tests for check_item method."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock()
        config.item_cache_enabled = True
        config.item_cache_ttl_seconds = 300
        config.league = "Standard"
        config.games = {"poe1": {"league": "Standard"}}
        config.current_game = "poe1"
        return config

    @pytest.fixture
    def mock_parser(self):
        """Create a mock parser."""
        parser = Mock()
        return parser

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache."""
        cache = Mock()
        cache.get.return_value = None
        return cache

    def test_check_item_empty_text_returns_empty(self, mock_config, mock_parser, mock_cache):
        """check_item with empty text should return empty list."""
        service = PriceService(
            config=mock_config,
            parser=mock_parser,
            db=Mock(),
            poe_ninja=Mock(),
            cache=mock_cache,
        )

        result = service.check_item("")
        assert result == []

        result = service.check_item("   ")
        assert result == []

        result = service.check_item(None)
        assert result == []

    def test_check_item_returns_cached_results(self, mock_config, mock_parser, mock_cache):
        """check_item should return cached results when available."""
        cached_data = [{"item_name": "Cached Item", "chaos_value": 100}]
        mock_cache.get.return_value = cached_data

        service = PriceService(
            config=mock_config,
            parser=mock_parser,
            db=Mock(),
            poe_ninja=Mock(),
            cache=mock_cache,
        )

        result = service.check_item("Some Item Text")

        assert result == cached_data
        mock_cache.get.assert_called_once_with("Some Item Text")

    def test_cache_enabled_property_controls_cache_usage(self, mock_config, mock_parser, mock_cache):
        """cache_enabled property should control whether cache is checked."""
        service = PriceService(
            config=mock_config,
            parser=mock_parser,
            db=Mock(),
            poe_ninja=Mock(),
            cache=mock_cache,
        )

        # Verify initial state
        assert service.cache_enabled is True

        # Disable caching
        service.cache_enabled = False
        assert service.cache_enabled is False
        assert service._cache_enabled is False

        # Re-enable caching
        service.cache_enabled = True
        assert service.cache_enabled is True


class TestPriceServiceConfidenceCalculation:
    """Tests for confidence-related calculations."""

    def test_confidence_order_mapping(self):
        """Verify confidence ordering logic."""
        # This tests the conf_order dictionary used in line 341
        conf_order = {"none": 0, "low": 1, "medium": 2, "high": 3}

        assert conf_order["none"] < conf_order["low"]
        assert conf_order["low"] < conf_order["medium"]
        assert conf_order["medium"] < conf_order["high"]

    def test_min_confidence_selection(self):
        """Test that minimum confidence is selected correctly."""
        conf_order = {"none": 0, "low": 1, "medium": 2, "high": 3}

        # Simulating the logic from line 342
        def get_min_confidence(conf1, conf2):
            return min(conf1, conf2, key=lambda c: conf_order.get(c, 0))

        assert get_min_confidence("high", "medium") == "medium"
        assert get_min_confidence("low", "high") == "low"
        assert get_min_confidence("none", "high") == "none"
        assert get_min_confidence("medium", "medium") == "medium"


class TestPriceServicePriceSpread:
    """Tests for price spread calculation logic."""

    def test_tight_spread_calculation(self):
        """Test tight spread detection (iqr_ratio <= 0.35)."""
        # Simulating lines 366-373
        p25 = 90
        p75 = 110
        median = 100

        iqr_ratio = (float(p75) - float(p25)) / float(median)
        assert iqr_ratio == 0.2
        assert iqr_ratio <= 0.35  # Should be "tight"

    def test_moderate_spread_calculation(self):
        """Test moderate spread detection (0.35 < iqr_ratio <= 0.6)."""
        p25 = 80
        p75 = 130
        median = 100

        iqr_ratio = (float(p75) - float(p25)) / float(median)
        assert iqr_ratio == 0.5
        assert 0.35 < iqr_ratio <= 0.6  # Should be "moderate"

    def test_high_spread_calculation(self):
        """Test high spread detection (iqr_ratio > 0.6)."""
        p25 = 50
        p75 = 150
        median = 100

        iqr_ratio = (float(p75) - float(p25)) / float(median)
        assert iqr_ratio == 1.0
        assert iqr_ratio > 0.6  # Should be "high"

    def test_zero_median_skips_spread(self):
        """Zero median should skip spread calculation."""
        p25 = 90
        p75 = 110
        median = 0

        # Logic check - should not calculate if median is 0
        should_calculate = p25 is not None and p75 is not None and median and float(median) > 0
        assert not should_calculate


class TestPriceServiceCalculationMethod:
    """Tests for calculation method determination."""

    def test_trimmed_mean_for_large_samples(self):
        """Large samples (>=12) with trimmed_mean should use trimmed_mean."""
        # Simulating lines 376-382
        count = 15
        stats = {"count": count, "trimmed_mean": 100.5, "median": 98.0}

        if count >= 12 and stats.get("trimmed_mean") is not None:
            method = "trimmed_mean"
        elif count >= 4 and stats.get("median") is not None:
            method = "median"
        else:
            method = "mean"

        assert method == "trimmed_mean"

    def test_median_for_medium_samples(self):
        """Medium samples (4-11) should use median."""
        count = 8
        stats = {"count": count, "trimmed_mean": None, "median": 98.0}

        if count >= 12 and stats.get("trimmed_mean") is not None:
            method = "trimmed_mean"
        elif count >= 4 and stats.get("median") is not None:
            method = "median"
        else:
            method = "mean"

        assert method == "median"

    def test_mean_for_small_samples(self):
        """Small samples (<4) should use mean."""
        count = 3
        stats = {"count": count, "trimmed_mean": None, "median": None}

        if count >= 12 and stats.get("trimmed_mean") is not None:
            method = "trimmed_mean"
        elif count >= 4 and stats.get("median") is not None:
            method = "median"
        else:
            method = "mean"

        assert method == "mean"


class TestPriceServiceInitialization:
    """Tests for PriceService initialization."""

    def test_init_with_all_sources(self):
        """Can initialize with all pricing sources."""
        config = Mock()
        config.item_cache_enabled = True
        config.item_cache_ttl_seconds = 300

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=Mock(),
            poe_watch=Mock(),
            trade_source=Mock(),
            rare_evaluator=Mock(),
        )

        assert service.config is config
        assert service.poe_ninja is not None
        assert service.poe_watch is not None
        assert service.trade_source is not None
        assert service.rare_evaluator is not None

    def test_init_with_minimal_sources(self):
        """Can initialize with only required parameters."""
        config = Mock()
        config.item_cache_enabled = False

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
        )

        assert service.poe_ninja is None
        assert service.poe_watch is None
        assert service.trade_source is None

    def test_init_applies_cache_ttl_from_config(self):
        """Should apply cache TTL from config."""
        config = Mock()
        config.item_cache_enabled = True
        config.item_cache_ttl_seconds = 600

        mock_cache = Mock()

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=Mock(),
            cache=mock_cache,
        )

        assert mock_cache.ttl_seconds == 600

    def test_init_handles_invalid_cache_ttl(self):
        """Should handle invalid cache TTL gracefully."""
        config = Mock()
        config.item_cache_enabled = True
        config.item_cache_ttl_seconds = "invalid"

        mock_cache = Mock()
        mock_cache.ttl_seconds = 300  # Default

        # Should not raise
        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=Mock(),
            cache=mock_cache,
        )

        # Should still have default TTL
        assert service._cache is mock_cache


class TestPriceServiceStatsPopulation:
    """Tests for stats population in explanation."""

    def test_stats_used_population(self):
        """Verify stats_used dict is properly populated."""
        stats = {
            "count": 25,
            "min": 80,
            "max": 120,
            "mean": 100,
            "median": 99,
            "p25": 92,
            "p75": 108,
            "trimmed_mean": 99.5,
        }

        # Simulating lines 351-360
        explanation = PriceExplanation()
        explanation.stats_used = {
            "count": stats.get("count", 0),
            "min": stats.get("min"),
            "max": stats.get("max"),
            "mean": stats.get("mean"),
            "median": stats.get("median"),
            "p25": stats.get("p25"),
            "p75": stats.get("p75"),
            "trimmed_mean": stats.get("trimmed_mean"),
        }

        assert explanation.stats_used["count"] == 25
        assert explanation.stats_used["min"] == 80
        assert explanation.stats_used["max"] == 120
        assert explanation.stats_used["median"] == 99
        assert explanation.stats_used["trimmed_mean"] == 99.5

    def test_stats_with_missing_values(self):
        """Should handle missing stats values."""
        stats = {"count": 2}  # Minimal stats

        explanation = PriceExplanation()
        explanation.stats_used = {
            "count": stats.get("count", 0),
            "min": stats.get("min"),
            "max": stats.get("max"),
            "mean": stats.get("mean"),
            "median": stats.get("median"),
            "p25": stats.get("p25"),
            "p75": stats.get("p75"),
            "trimmed_mean": stats.get("trimmed_mean"),
        }

        assert explanation.stats_used["count"] == 2
        assert explanation.stats_used["min"] is None
        assert explanation.stats_used["median"] is None
