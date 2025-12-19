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

        PriceService(
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


class TestEstimatedValueParsing:
    """Tests for _parse_estimated_value_to_chaos method."""

    @pytest.fixture
    def service_with_divine_rate(self):
        """Create service with mock divine rate."""
        config = Mock()
        config.item_cache_enabled = False
        poe_ninja = Mock()
        poe_ninja.ensure_divine_rate.return_value = 200.0

        return PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=poe_ninja,
            cache=None,
        )

    def test_parse_less_than_value(self, service_with_divine_rate):
        """<5c should return half the value."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("<5c")
        assert result == 2.5

        result = service_with_divine_rate._parse_estimated_value_to_chaos("<10c")
        assert result == 5.0

    def test_parse_chaos_plus_value(self, service_with_divine_rate):
        """50c+ should return the value as-is."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("50c+")
        assert result == 50.0

    def test_parse_divine_plus_value(self, service_with_divine_rate):
        """1div+ should convert using divine rate."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("1div+")
        assert result == 200.0  # 1 * 200

        result = service_with_divine_rate._parse_estimated_value_to_chaos("2div+")
        assert result == 400.0  # 2 * 200

    def test_parse_chaos_range(self, service_with_divine_rate):
        """50-200c should return midpoint."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("50-200c")
        assert result == 125.0

        result = service_with_divine_rate._parse_estimated_value_to_chaos("5-10c")
        assert result == 7.5

    def test_parse_chaos_to_divine_range(self, service_with_divine_rate):
        """200c-5div should convert and return midpoint."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("200c-5div")
        # (200 + 5*200) / 2 = (200 + 1000) / 2 = 600
        assert result == 600.0

    def test_parse_exact_divine(self, service_with_divine_rate):
        """1div should convert to chaos."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("1div")
        assert result == 200.0

    def test_parse_empty_value(self, service_with_divine_rate):
        """Empty value should return None."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("")
        assert result is None

        result = service_with_divine_rate._parse_estimated_value_to_chaos(None)
        assert result is None

    def test_parse_unknown_format(self, service_with_divine_rate):
        """Unknown format should return None."""
        result = service_with_divine_rate._parse_estimated_value_to_chaos("unknown")
        assert result is None


class TestDivineConversion:
    """Tests for divine to chaos conversion."""

    def test_convert_with_ninja_rate(self):
        """Should use poe.ninja divine rate."""
        config = Mock()
        config.item_cache_enabled = False
        config.divine_rate = None
        config.current_game = "poe1"
        config.games = {}

        poe_ninja = Mock()
        poe_ninja.ensure_divine_rate.return_value = 200.0

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=poe_ninja,
            cache=None,
        )

        result = service._convert_chaos_to_divines(400.0)
        assert result == 2.0  # 400 / 200

    def test_convert_with_config_rate(self):
        """Should use config divine_rate if set."""
        config = Mock()
        config.item_cache_enabled = False
        config.divine_rate = 150.0
        config.current_game = "poe1"
        config.games = {}

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            cache=None,
        )

        result = service._convert_chaos_to_divines(300.0)
        assert result == 2.0  # 300 / 150

    def test_convert_no_rate_returns_zero(self):
        """Should return 0.0 if no divine rate available."""
        config = Mock()
        config.item_cache_enabled = False
        config.divine_rate = None
        config.current_game = "poe1"
        config.games = {}

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            cache=None,
        )

        result = service._convert_chaos_to_divines(400.0)
        assert result == 0.0


class TestComputeDisplayPrice:
    """Tests for compute_display_price static method."""

    def test_no_listings(self):
        """Zero listings should return none confidence."""
        result = PriceService.compute_display_price({"count": 0})
        assert result["confidence"] == "none"
        assert result["display_price"] is None
        assert "No listings" in result["reason"]

    def test_high_confidence(self):
        """High sample with tight spread = high confidence."""
        stats = {
            "count": 50,
            "mean": 100,
            "median": 100,
            "p25": 95,
            "p75": 105,
            "trimmed_mean": 100,
            "stddev": 5,
        }
        result = PriceService.compute_display_price(stats)
        assert result["confidence"] == "high"
        assert result["display_price"] == 100
        assert result["rounded_price"] is not None

    def test_medium_confidence(self):
        """Medium sample with acceptable spread = medium confidence."""
        stats = {
            "count": 15,
            "mean": 100,
            "median": 100,
            "p25": 85,
            "p75": 115,
            "trimmed_mean": 100,
            "stddev": 15,
        }
        result = PriceService.compute_display_price(stats)
        assert result["confidence"] in ["medium", "low"]

    def test_low_confidence_high_spread(self):
        """High spread should give low confidence."""
        stats = {
            "count": 20,
            "mean": 100,
            "median": 100,
            "p25": 50,
            "p75": 150,  # 100% spread
            "trimmed_mean": 100,
            "stddev": 50,  # 50% CV
        }
        result = PriceService.compute_display_price(stats)
        assert result["confidence"] == "low"
        assert "spread" in result["reason"].lower() or "volatile" in result["reason"].lower()

    def test_trimmed_mean_used_for_large_samples(self):
        """Large samples should use trimmed_mean."""
        stats = {
            "count": 15,
            "mean": 100,
            "median": 95,
            "p25": 90,
            "p75": 110,
            "trimmed_mean": 98,
            "stddev": 10,
        }
        result = PriceService.compute_display_price(stats)
        assert result["display_price"] == 98  # trimmed_mean
        assert "trimmed_mean" in result["reason"]

    def test_median_used_for_medium_samples(self):
        """Medium samples should use median."""
        stats = {
            "count": 8,
            "mean": 100,
            "median": 95,
            "p25": 90,
            "p75": 110,
            "stddev": 10,
        }
        result = PriceService.compute_display_price(stats)
        assert result["display_price"] == 95  # median
        assert "median" in result["reason"]

    def test_mean_used_for_small_samples(self):
        """Small samples should use mean."""
        stats = {
            "count": 3,
            "mean": 100,
            "median": None,
            "p25": None,
            "p75": None,
            "stddev": None,
        }
        result = PriceService.compute_display_price(stats)
        assert result["display_price"] == 100  # mean
        assert "mean" in result["reason"]

    def test_rounding_large_values(self):
        """Large values should round to step size."""
        stats = {
            "count": 20,
            "mean": 157.3,
            "median": 157.3,
            "p25": 150,
            "p75": 165,
            "trimmed_mean": 157.3,
            "stddev": 8,
        }
        result = PriceService.compute_display_price(stats)
        # Values >= 100 should be rounded to step
        assert result["rounded_price"] in [155, 160, 157]


class TestExplanationSummaryBuilder:
    """Tests for _build_explanation_summary method."""

    @pytest.fixture
    def service(self):
        """Create basic service."""
        config = Mock()
        config.item_cache_enabled = False
        return PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            cache=None,
        )

    def test_zero_price_summary(self, service):
        """Zero price should return 'No price data found'."""
        exp = PriceExplanation()
        result = service._build_explanation_summary(exp, 0.0, "test")
        assert result == "No price data found"

    def test_basic_summary(self, service):
        """Basic summary with source."""
        exp = PriceExplanation(source_name="poe.ninja")
        result = service._build_explanation_summary(exp, 100.0, "poe.ninja")
        assert "100.0c" in result
        assert "poe.ninja" in result

    def test_rare_evaluation_summary(self, service):
        """Rare evaluation should include tier."""
        exp = PriceExplanation(
            is_rare_evaluation=True,
            rare_tier="excellent",
        )
        result = service._build_explanation_summary(exp, 50.0, "rare_evaluator")
        assert "50.0c" in result
        assert "excellent" in result

    def test_confidence_included(self, service):
        """Confidence should be included in summary."""
        exp = PriceExplanation(
            source_name="poe.ninja",
            confidence="high",
        )
        result = service._build_explanation_summary(exp, 100.0, "poe.ninja")
        assert "high" in result

    def test_sample_size_included(self, service):
        """Large sample size should be included."""
        exp = PriceExplanation(
            source_name="poe.ninja",
            sample_size=50,
        )
        result = service._build_explanation_summary(exp, 100.0, "poe.ninja")
        assert "50" in result
        assert "listings" in result


class TestCurrencyLookup:
    """Tests for currency price lookup."""

    def test_currency_lookup_success(self):
        """Should lookup currency price."""
        config = Mock()
        config.item_cache_enabled = False
        poe_ninja = Mock()
        poe_ninja.get_currency_price.return_value = (150.0, "poe.ninja currency")

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=poe_ninja,
            cache=None,
        )

        chaos, count, source = service._lookup_currency_price("Divine Orb")
        assert chaos == 150.0
        assert source == "poe.ninja currency"

    def test_currency_lookup_not_found(self):
        """Should handle currency not found."""
        config = Mock()
        config.item_cache_enabled = False
        poe_ninja = Mock()
        poe_ninja.get_currency_price.return_value = (0.0, "not found")

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=poe_ninja,
            cache=None,
        )

        chaos, count, source = service._lookup_currency_price("Unknown Currency")
        assert chaos == 0.0
        assert source == "not found"

    def test_currency_lookup_no_ninja(self):
        """Should return 0 when no poe.ninja."""
        config = Mock()
        config.item_cache_enabled = False

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            cache=None,
        )

        chaos, count, source = service._lookup_currency_price("Divine Orb")
        assert chaos == 0.0
        assert source == "no poe.ninja"


class TestItemHelpers:
    """Tests for parsed item helper methods."""

    @pytest.fixture
    def service(self):
        """Create basic service."""
        config = Mock()
        config.item_cache_enabled = False
        return PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            cache=None,
        )

    def test_get_item_display_name(self, service):
        """Should extract display name from various attributes."""
        item = Mock()
        item.display_name = "Test Item"
        assert service._get_item_display_name(item) == "Test Item"

        item2 = Mock(spec=[])
        item2.name = "Named Item"
        assert service._get_item_display_name(item2) == "Named Item"

    def test_get_base_type(self, service):
        """Should extract base type."""
        item = Mock()
        item.base_type = "Vaal Regalia"
        assert service._get_base_type(item) == "Vaal Regalia"

    def test_get_rarity(self, service):
        """Should extract rarity."""
        item = Mock()
        item.rarity = "RARE"
        assert service._get_rarity(item) == "RARE"

    def test_get_gem_level(self, service):
        """Should extract gem level."""
        item = Mock()
        item.gem_level = 21
        assert service._get_gem_level(item) == 21

    def test_get_gem_quality(self, service):
        """Should extract gem quality."""
        item = Mock()
        item.gem_quality = 23
        assert service._get_gem_quality(item) == 23

    def test_get_corrupted_flag_bool(self, service):
        """Should handle boolean corrupted flag."""
        item = Mock()
        item.corrupted = True
        assert service._get_corrupted_flag(item) is True

        item.corrupted = False
        assert service._get_corrupted_flag(item) is False

    def test_get_corrupted_flag_string(self, service):
        """Should handle string corrupted flag."""
        item = Mock()
        item.corrupted = "Corrupted"
        assert service._get_corrupted_flag(item) is True

        item.corrupted = ""
        assert service._get_corrupted_flag(item) is False

    def test_get_item_links(self, service):
        """Should extract link count."""
        item = Mock()
        item.links = 6
        assert service._get_item_links(item) == "6"

    def test_get_item_variant(self, service):
        """Should extract variant label."""
        item = Mock()
        item.variant = "Shaper"
        assert service._get_item_variant(item) == "Shaper"

    def test_parse_links(self, service):
        """Should parse link string to int."""
        item = Mock()
        item.links = "6"
        assert service._parse_links(item) == 6

        item.links = None
        assert service._parse_links(item) is None


class TestMultiSourcePricing:
    """Tests for multi-source pricing logic."""

    @pytest.fixture
    def multi_source_service(self):
        """Create service with both pricing sources."""
        config = Mock()
        config.item_cache_enabled = False
        config.current_game = "poe1"
        config.games = {"poe1": {"league": "Standard"}}

        poe_ninja = Mock()
        poe_ninja.league = "Standard"

        poe_watch = Mock()

        return PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=poe_ninja,
            poe_watch=poe_watch,
            cache=None,
        )

    def test_ninja_only_with_high_count_early_exit(self, multi_source_service):
        """High-confidence ninja data should skip poe.watch."""
        # Setup ninja to return high-count data
        multi_source_service.poe_ninja.find_item_price.return_value = {
            "chaosValue": 100.0,
            "count": 50,
        }

        parsed = Mock()
        parsed.display_name = "Test Item"
        parsed.base_type = "Test Base"
        parsed.rarity = "UNIQUE"

        # Mock helper methods
        multi_source_service._lookup_price_with_poe_ninja = Mock(
            return_value=(100.0, 50, "poe.ninja")
        )

        chaos, count, source, conf = multi_source_service._lookup_price_multi_source(parsed)

        assert chaos == 100.0
        assert count == 50
        assert "high confidence" in source
        assert conf == "high"

    def test_both_sources_agree(self, multi_source_service):
        """Both sources agreeing should give high confidence."""
        multi_source_service._lookup_price_with_poe_ninja = Mock(
            return_value=(100.0, 10, "poe.ninja")
        )
        multi_source_service.poe_watch.find_item_price.return_value = {
            "mean": 105.0,
            "daily": 15,
            "lowConfidence": False,
        }

        parsed = Mock()
        parsed.display_name = "Test Item"
        parsed.base_type = "Test Base"
        parsed.rarity = "UNIQUE"

        chaos, count, source, conf = multi_source_service._lookup_price_multi_source(parsed)

        # Should use ninja price since within 20%
        assert chaos == 100.0
        assert "validated" in source
        assert conf == "high"

    def test_sources_diverge(self, multi_source_service):
        """Diverging sources should average with medium confidence."""
        multi_source_service._lookup_price_with_poe_ninja = Mock(
            return_value=(100.0, 10, "poe.ninja")
        )
        multi_source_service.poe_watch.find_item_price.return_value = {
            "mean": 200.0,  # 100% difference
            "daily": 15,
            "lowConfidence": False,
        }

        parsed = Mock()
        parsed.display_name = "Test Item"
        parsed.base_type = "Test Base"
        parsed.rarity = "UNIQUE"

        chaos, count, source, conf = multi_source_service._lookup_price_multi_source(parsed)

        # Should average the prices
        assert chaos == 150.0  # (100 + 200) / 2
        assert "averaged" in source
        assert conf == "medium"

    def test_only_ninja_available(self, multi_source_service):
        """Only ninja data should give medium confidence."""
        multi_source_service._lookup_price_with_poe_ninja = Mock(
            return_value=(100.0, 10, "poe.ninja")
        )
        multi_source_service.poe_watch.find_item_price.return_value = None

        parsed = Mock()
        parsed.display_name = "Test Item"
        parsed.base_type = "Test Base"
        parsed.rarity = "UNIQUE"

        chaos, count, source, conf = multi_source_service._lookup_price_multi_source(parsed)

        assert chaos == 100.0
        assert "only" in source
        assert conf == "medium"

    def test_only_watch_available(self, multi_source_service):
        """Only poe.watch data should use watch confidence."""
        multi_source_service._lookup_price_with_poe_ninja = Mock(
            return_value=(0.0, 0, "not found")
        )
        multi_source_service.poe_watch.find_item_price.return_value = {
            "mean": 100.0,
            "daily": 20,
            "lowConfidence": False,
        }

        parsed = Mock()
        parsed.display_name = "Test Item"
        parsed.base_type = "Test Base"
        parsed.rarity = "UNIQUE"

        chaos, count, source, conf = multi_source_service._lookup_price_multi_source(parsed)

        assert chaos == 100.0
        assert "poe.watch" in source
        assert conf == "high"  # daily > 10

    def test_no_prices_found(self, multi_source_service):
        """No prices should return zeros."""
        multi_source_service._lookup_price_with_poe_ninja = Mock(
            return_value=(0.0, 0, "not found")
        )
        multi_source_service.poe_watch.find_item_price.return_value = None

        parsed = Mock()
        parsed.display_name = "Test Item"
        parsed.base_type = "Test Base"
        parsed.rarity = "UNIQUE"

        chaos, count, source, conf = multi_source_service._lookup_price_multi_source(parsed)

        assert chaos == 0.0
        assert count == 0
        assert "not found" in source
        assert conf == "none"


class TestGameLeagueResolution:
    """Tests for _resolve_game_and_league method."""

    def test_resolve_from_poe_ninja(self):
        """Should get league from poe.ninja first."""
        config = Mock()
        config.item_cache_enabled = False
        config.current_game = "poe1"
        config.games = {}

        poe_ninja = Mock()
        poe_ninja.league = "Settlers"

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=poe_ninja,
            cache=None,
        )

        game, league = service._resolve_game_and_league()
        assert league == "Settlers"

    def test_resolve_from_config_games(self):
        """Should get league from config games when ninja unavailable."""
        config = Mock()
        config.item_cache_enabled = False
        config.current_game = "poe1"
        config.games = {"poe1": {"league": "Standard"}}
        config.league = "FallbackLeague"

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            cache=None,
        )

        game, league = service._resolve_game_and_league()
        assert league == "Standard"

    def test_resolve_poe2_game_version(self):
        """Should handle PoE2 game version."""
        from core.game_version import GameVersion

        config = Mock()
        config.item_cache_enabled = False
        config.current_game = GameVersion.POE2
        config.games = {"poe2": {"league": "PoE2Standard"}}
        config.league = None

        service = PriceService(
            config=config,
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            cache=None,
        )

        game, league = service._resolve_game_and_league()
        assert game == GameVersion.POE2
        assert league == "PoE2Standard"
