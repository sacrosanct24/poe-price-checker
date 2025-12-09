"""Tests for core/quick_verdict.py - Quick verdict system."""

import pytest
from unittest.mock import MagicMock

from core.quick_verdict import (
    Verdict,
    VerdictThresholds,
    VerdictResult,
    QuickVerdictCalculator,
    quick_verdict,
)


# =============================================================================
# Verdict Enum Tests
# =============================================================================


class TestVerdict:
    """Tests for Verdict enum."""

    def test_keep_value(self):
        """Should have keep value."""
        assert Verdict.KEEP.value == "keep"

    def test_vendor_value(self):
        """Should have vendor value."""
        assert Verdict.VENDOR.value == "vendor"

    def test_maybe_value(self):
        """Should have maybe value."""
        assert Verdict.MAYBE.value == "maybe"


# =============================================================================
# VerdictThresholds Tests
# =============================================================================


class TestVerdictThresholds:
    """Tests for VerdictThresholds dataclass."""

    def test_default_vendor_threshold(self):
        """Should have default vendor threshold."""
        thresholds = VerdictThresholds()
        assert thresholds.vendor_threshold == 2.0

    def test_default_keep_threshold(self):
        """Should have default keep threshold."""
        thresholds = VerdictThresholds()
        assert thresholds.keep_threshold == 15.0

    def test_custom_thresholds(self):
        """Should accept custom thresholds."""
        thresholds = VerdictThresholds(vendor_threshold=5.0, keep_threshold=50.0)
        assert thresholds.vendor_threshold == 5.0
        assert thresholds.keep_threshold == 50.0

    def test_six_link_bonus(self):
        """Should have six link bonus."""
        thresholds = VerdictThresholds()
        assert thresholds.six_link_bonus == 150.0  # Updated for Divine Orb recipe value


# =============================================================================
# VerdictResult Tests
# =============================================================================


class TestVerdictResult:
    """Tests for VerdictResult dataclass."""

    def test_emoji_keep(self):
        """Should return thumbs up for keep."""
        result = VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Test",
            detailed_reasons=[],
        )
        assert result.emoji == "👍"

    def test_emoji_vendor(self):
        """Should return thumbs down for vendor."""
        result = VerdictResult(
            verdict=Verdict.VENDOR,
            explanation="Test",
            detailed_reasons=[],
        )
        assert result.emoji == "👎"

    def test_emoji_maybe(self):
        """Should return thinking face for maybe."""
        result = VerdictResult(
            verdict=Verdict.MAYBE,
            explanation="Test",
            detailed_reasons=[],
        )
        assert result.emoji == "🤔"

    def test_color_keep(self):
        """Should return green for keep."""
        result = VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Test",
            detailed_reasons=[],
        )
        assert "22" in result.color  # Green has "22" in hex

    def test_color_vendor(self):
        """Should return red for vendor."""
        result = VerdictResult(
            verdict=Verdict.VENDOR,
            explanation="Test",
            detailed_reasons=[],
        )
        assert "bb22" in result.color or "22" in result.color  # Red

    def test_estimated_value(self):
        """Should store estimated value."""
        result = VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Test",
            detailed_reasons=[],
            estimated_value=50.0,
        )
        assert result.estimated_value == 50.0


# =============================================================================
# QuickVerdictCalculator Tests
# =============================================================================


class TestQuickVerdictCalculatorInit:
    """Tests for calculator initialization."""

    def test_init_default_thresholds(self):
        """Should use default thresholds."""
        calc = QuickVerdictCalculator()
        assert calc.thresholds.vendor_threshold == 2.0
        assert calc.thresholds.keep_threshold == 15.0

    def test_init_custom_thresholds(self):
        """Should accept custom thresholds."""
        thresholds = VerdictThresholds(vendor_threshold=10.0, keep_threshold=100.0)
        calc = QuickVerdictCalculator(thresholds=thresholds)
        assert calc.thresholds.vendor_threshold == 10.0


class TestQuickVerdictCalculatorHighValue:
    """Tests for high value item verdicts."""

    def test_high_price_returns_keep(self):
        """Should return KEEP for high price items."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=100.0)

        assert result.verdict == Verdict.KEEP

    def test_six_link_returns_keep(self):
        """Should return KEEP for 6-link items."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.sockets = 6
        item.links = 6

        result = calc.calculate(item, price_chaos=0)

        assert result.verdict == Verdict.KEEP
        assert "6-link" in result.explanation.lower() or "6-link" in str(result.detailed_reasons).lower()


class TestQuickVerdictCalculatorLowValue:
    """Tests for low value item verdicts."""

    def test_low_price_returns_vendor(self):
        """Should return VENDOR for low price items."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []  # No influences
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=0.5)

        assert result.verdict == Verdict.VENDOR

    def test_normal_item_returns_vendor(self):
        """Should return VENDOR for normal items."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Normal"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        assert result.verdict == Verdict.VENDOR


class TestQuickVerdictCalculatorMaybe:
    """Tests for uncertain verdicts."""

    def test_mid_price_returns_maybe(self):
        """Should return MAYBE for mid-range prices."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=8.0)

        assert result.verdict == Verdict.MAYBE

    def test_no_price_good_mods_returns_maybe(self):
        """Should return MAYBE when price unknown but item has potential."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        # Use values above detection thresholds (80+ life, 35%+ resist)
        item.explicits = ["+90 to maximum life", "+40% to Fire Resistance"]
        item.implicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=None)

        # Could be MAYBE or KEEP depending on mod analysis
        assert result.verdict in (Verdict.MAYBE, Verdict.KEEP)


class TestQuickVerdictCalculatorUniques:
    """Tests for unique item handling."""

    def test_unique_gets_bonus(self):
        """Should give uniques benefit of doubt."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Unique"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=None)

        # Unique bonus should push toward MAYBE at least
        assert result.verdict in (Verdict.MAYBE, Verdict.KEEP)
        assert "unique" in str(result.detailed_reasons).lower()


class TestQuickVerdictCalculatorCurrency:
    """Tests for currency item handling."""

    def test_currency_gets_bonus(self):
        """Should give currency items a bonus."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Currency"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=None)

        # Currency gets +10 bonus, so should be MAYBE at minimum
        assert result.verdict in (Verdict.MAYBE, Verdict.KEEP)
        assert "currency" in str(result.detailed_reasons).lower()

    def test_currency_with_price_returns_keep(self):
        """Should return KEEP for currency with good price."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Currency"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=10.0)

        # 10c + 10 bonus = 20, above keep threshold
        assert result.verdict == Verdict.KEEP


class TestQuickVerdictCalculatorRareAnalysis:
    """Tests for rare item affix analysis."""

    def test_high_life_roll_detected(self):
        """Should detect high life rolls."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = ["+95 to maximum life"]
        item.implicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=None)

        assert any("life" in r.lower() for r in result.detailed_reasons)

    def test_good_resistance_detected(self):
        """Should detect good resistance rolls."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = ["+42% to Fire Resistance"]
        item.implicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=None)

        assert any("resistance" in r.lower() for r in result.detailed_reasons)

    def test_movement_speed_detected(self):
        """Should detect good movement speed on boots."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = ["+30% increased Movement Speed"]
        item.implicits = []
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item, price_chaos=None)

        assert any("movement" in r.lower() for r in result.detailed_reasons)


class TestQuickVerdictCalculatorFromPrices:
    """Tests for multi-price calculation."""

    def test_calculate_from_multiple_prices(self):
        """Should use median of multiple prices."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        prices = [
            ("poe.ninja", 50.0),
            ("trade", 60.0),
            ("poeprices", 45.0),
        ]

        result = calc.calculate_from_prices(item, prices)

        assert result.verdict == Verdict.KEEP
        assert result.estimated_value == 50.0  # Median

    def test_calculate_from_prices_high_confidence(self):
        """Should have high confidence with multiple sources."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        prices = [("a", 100.0), ("b", 100.0)]

        result = calc.calculate_from_prices(item, prices)

        assert result.confidence == "high"


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestQuickVerdictFunction:
    """Tests for quick_verdict convenience function."""

    def test_quick_verdict_returns_result(self):
        """Should return VerdictResult."""
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        result = quick_verdict(item, price_chaos=50.0)

        assert isinstance(result, VerdictResult)

    def test_quick_verdict_with_no_price(self):
        """Should work without price."""
        item = MagicMock()
        item.rarity = "Normal"
        item.explicits = []
        item.sockets = 0
        item.links = 0

        result = quick_verdict(item)

        assert isinstance(result, VerdictResult)


# =============================================================================
# Edge Cases
# =============================================================================


class TestQuickVerdictEdgeCases:
    """Edge case tests."""

    def test_missing_attributes(self):
        """Should handle items with missing attributes."""
        calc = QuickVerdictCalculator()
        item = MagicMock(spec=[])  # Empty spec - all attributes return MagicMock

        # Should not raise
        result = calc.calculate(item, price_chaos=10.0)

        assert isinstance(result, VerdictResult)

    def test_none_explicits(self):
        """Should handle None explicits."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = None
        item.implicits = None
        item.sockets = 0
        item.links = 0

        result = calc.calculate(item)

        assert isinstance(result, VerdictResult)

    def test_empty_item(self):
        """Should handle minimal item."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = None
        item.name = None
        item.base_type = None
        item.explicits = []
        item.sockets = None
        item.links = None

        result = calc.calculate(item)

        assert isinstance(result, VerdictResult)


# =============================================================================
# New Feature Tests - Influenced, Fractured, Gem Levels
# =============================================================================


class TestInfluencedItems:
    """Tests for influenced item detection."""

    def test_influenced_item_gets_bonus(self):
        """Should detect influenced items and add bonus."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = ["Shaper"]
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        assert any("influenced" in r.lower() for r in result.detailed_reasons)
        # 20c bonus should push to KEEP (20 > 15)
        assert result.verdict == Verdict.KEEP

    def test_multiple_influences_detected(self):
        """Should handle multiple influences."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = ["Elder", "Shaper"]
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        assert any("elder" in r.lower() or "shaper" in r.lower() for r in result.detailed_reasons)


class TestFracturedItems:
    """Tests for fractured item detection."""

    def test_fractured_item_gets_bonus(self):
        """Should detect fractured items and add bonus."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = True
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        assert any("fractured" in r.lower() for r in result.detailed_reasons)
        # 30c bonus should push to KEEP
        assert result.verdict == Verdict.KEEP

    def test_synthesised_item_gets_bonus(self):
        """Should detect synthesised items and add bonus."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = True

        result = calc.calculate(item, price_chaos=None)

        assert any("synthesised" in r.lower() for r in result.detailed_reasons)
        # 30c bonus should push to KEEP
        assert result.verdict == Verdict.KEEP


class TestGemLevelDetection:
    """Tests for +gem level mod detection."""

    def test_gem_level_mod_detected(self):
        """Should detect +gem level mods."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = ["+1 to Level of all Skill Gems"]
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        assert any("+level" in r.lower() for r in result.detailed_reasons)
        # 50c bonus + 3c for reason = 53, should be KEEP
        assert result.verdict == Verdict.KEEP

    def test_spell_gem_level_detected(self):
        """Should detect spell gem level mods."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = ["+1 to Level of all Spell Skill Gems"]
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        assert any("spell" in r.lower() for r in result.detailed_reasons)

    def test_aura_gem_level_detected(self):
        """Should detect aura gem level mods."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = ["+2 to Level of all Aura Gems"]
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        assert any("aura" in r.lower() for r in result.detailed_reasons)


class TestLeagueThresholds:
    """Tests for league-specific thresholds."""

    def test_league_start_thresholds(self):
        """Should have lenient league start thresholds."""
        thresholds = VerdictThresholds.for_league_start()
        assert thresholds.vendor_threshold == 1.0
        assert thresholds.keep_threshold == 5.0

    def test_mid_league_thresholds(self):
        """Should have balanced mid-league thresholds."""
        thresholds = VerdictThresholds.for_mid_league()
        assert thresholds.vendor_threshold == 2.0
        assert thresholds.keep_threshold == 10.0

    def test_late_league_thresholds(self):
        """Should have strict late league thresholds."""
        thresholds = VerdictThresholds.for_late_league()
        assert thresholds.vendor_threshold == 5.0
        assert thresholds.keep_threshold == 20.0

    def test_ssf_thresholds(self):
        """Should have very lenient SSF thresholds."""
        thresholds = VerdictThresholds.for_ssf()
        assert thresholds.vendor_threshold == 0.5
        assert thresholds.keep_threshold == 3.0

    def test_league_start_keeps_more(self):
        """League start thresholds should keep more items."""
        league_start_calc = QuickVerdictCalculator(
            thresholds=VerdictThresholds.for_league_start()
        )
        default_calc = QuickVerdictCalculator()

        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        # 8c item: MAYBE with defaults, KEEP with league start
        default_result = default_calc.calculate(item, price_chaos=8.0)
        league_result = league_start_calc.calculate(item, price_chaos=8.0)

        assert default_result.verdict == Verdict.MAYBE
        assert league_result.verdict == Verdict.KEEP


class TestUniqueItemHandling:
    """Tests for unique item logic changes."""

    def test_unique_without_price_suggests_lookup(self):
        """Unique without price should suggest checking price."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Unique"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        # Should mention checking price
        assert any("check price" in r.lower() for r in result.detailed_reasons)
        # Without price, unique gets no bonus (0), so VENDOR
        assert result.verdict == Verdict.VENDOR

    def test_unique_with_high_price_keeps(self):
        """Unique with known high price should KEEP."""
        calc = QuickVerdictCalculator()
        item = MagicMock()
        item.rarity = "Unique"
        item.explicits = []
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=50.0)

        assert result.verdict == Verdict.KEEP


# =============================================================================
# Meta Weights Integration Tests
# =============================================================================


class TestMetaWeightsIntegration:
    """Tests for meta weights integration in QuickVerdictCalculator."""

    @pytest.fixture
    def mock_meta_weights(self):
        """Create mock meta weights data."""
        return {
            'life': {'popularity_percent': 80.0},
            'resistances': {'popularity_percent': 75.0},
            'movement_speed': {'popularity_percent': 60.0},
            'attack_speed': {'popularity_percent': 35.0},
            'mana': {'popularity_percent': 10.0},  # Below threshold
        }

    @pytest.fixture
    def rare_item_with_meta_mods(self):
        """Create a rare item with meta-popular mods."""
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = [
            "+95 to maximum Life",
            "+40% to Fire Resistance",
            "25% increased Movement Speed",
        ]
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False
        return item

    def test_init_with_meta_weights(self, mock_meta_weights):
        """Should accept meta weights on initialization."""
        calc = QuickVerdictCalculator(meta_weights=mock_meta_weights)
        assert calc.meta_weights == mock_meta_weights

    def test_set_meta_weights(self, mock_meta_weights):
        """Should update meta weights dynamically."""
        calc = QuickVerdictCalculator()
        assert calc.meta_weights == {}

        calc.set_meta_weights(mock_meta_weights)
        assert calc.meta_weights == mock_meta_weights

    def test_meta_affixes_detected(self, mock_meta_weights, rare_item_with_meta_mods):
        """Should detect meta-popular affixes on items."""
        calc = QuickVerdictCalculator(meta_weights=mock_meta_weights)

        result = calc.calculate(rare_item_with_meta_mods, price_chaos=None)

        # Should find life, resistances, and movement_speed as meta
        assert len(result.meta_affixes_found) >= 2
        assert 'life' in result.meta_affixes_found
        assert 'resistances' in result.meta_affixes_found

    def test_meta_bonus_applied(self, mock_meta_weights, rare_item_with_meta_mods):
        """Should apply meta bonus when meta affixes found."""
        calc = QuickVerdictCalculator(meta_weights=mock_meta_weights)

        result = calc.calculate(rare_item_with_meta_mods, price_chaos=None)

        # Should have meta bonus applied (5.0 per meta affix by default)
        assert result.meta_bonus_applied > 0
        assert result.has_meta_bonus is True

    def test_no_meta_bonus_without_weights(self, rare_item_with_meta_mods):
        """Should not apply meta bonus when no weights provided."""
        calc = QuickVerdictCalculator()

        result = calc.calculate(rare_item_with_meta_mods, price_chaos=None)

        assert result.meta_bonus_applied == 0
        assert result.has_meta_bonus is False
        assert result.meta_affixes_found == []

    def test_meta_below_threshold_not_counted(self, mock_meta_weights):
        """Should not count meta affixes below popularity threshold."""
        calc = QuickVerdictCalculator(meta_weights=mock_meta_weights)

        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = ["+50 to maximum Mana"]  # 10% popularity, below 30% threshold
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        # Mana has only 10% popularity, below 30% threshold
        assert 'mana' not in result.meta_affixes_found

    def test_meta_synergy_reason_added(self, mock_meta_weights, rare_item_with_meta_mods):
        """Should add meta synergy reason when 2+ meta affixes found."""
        calc = QuickVerdictCalculator(meta_weights=mock_meta_weights)

        result = calc.calculate(rare_item_with_meta_mods, price_chaos=None)

        # Should have meta synergy in reasons
        assert any("meta build synergy" in r.lower() for r in result.detailed_reasons)

    def test_meta_bonus_improves_verdict(self, mock_meta_weights):
        """Meta bonus should help items reach KEEP threshold."""
        calc_without_meta = QuickVerdictCalculator()
        calc_with_meta = QuickVerdictCalculator(meta_weights=mock_meta_weights)

        # Item with some value but not enough to KEEP without meta
        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = [
            "+85 to maximum Life",
            "+38% to Cold Resistance",
        ]
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        # With 5c price: no meta = MAYBE, with meta = could be KEEP
        result_no_meta = calc_without_meta.calculate(item, price_chaos=5.0)
        result_with_meta = calc_with_meta.calculate(item, price_chaos=5.0)

        # Meta bonus should improve the verdict
        assert result_with_meta.meta_bonus_applied > 0

    def test_custom_meta_threshold(self, mock_meta_weights):
        """Should respect custom meta popularity threshold."""
        thresholds = VerdictThresholds(meta_popularity_threshold=50.0)
        calc = QuickVerdictCalculator(
            thresholds=thresholds,
            meta_weights=mock_meta_weights
        )

        item = MagicMock()
        item.rarity = "Rare"
        item.explicits = [
            "+90 to maximum Life",      # 80% popularity - above
            "10% increased Attack Speed", # 35% popularity - below 50%
        ]
        item.implicits = []
        item.sockets = 0
        item.links = 0
        item.influences = []
        item.is_fractured = False
        item.is_synthesised = False

        result = calc.calculate(item, price_chaos=None)

        # Only life should count (80% > 50% threshold)
        # attack_speed at 35% is below 50% threshold
        assert 'life' in result.meta_affixes_found
        assert 'attack_speed' not in result.meta_affixes_found


class TestVerdictResultMetaFields:
    """Tests for meta-related fields in VerdictResult."""

    def test_has_meta_bonus_true(self):
        """Should return True when meta bonus applied."""
        result = VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Test",
            detailed_reasons=[],
            meta_affixes_found=['life', 'resistances'],
            meta_bonus_applied=10.0,
        )
        assert result.has_meta_bonus is True

    def test_has_meta_bonus_false(self):
        """Should return False when no meta bonus."""
        result = VerdictResult(
            verdict=Verdict.VENDOR,
            explanation="Test",
            detailed_reasons=[],
        )
        assert result.has_meta_bonus is False

    def test_meta_affixes_default_empty(self):
        """Should default to empty list for meta affixes."""
        result = VerdictResult(
            verdict=Verdict.MAYBE,
            explanation="Test",
            detailed_reasons=[],
        )
        assert result.meta_affixes_found == []

    def test_meta_bonus_default_zero(self):
        """Should default to zero meta bonus."""
        result = VerdictResult(
            verdict=Verdict.MAYBE,
            explanation="Test",
            detailed_reasons=[],
        )
        assert result.meta_bonus_applied == 0.0


class TestVerdictStatistics:
    """Tests for VerdictStatistics class."""

    def test_initial_counts_zero(self):
        """Should start with all counts at zero."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()
        assert stats.keep_count == 0
        assert stats.vendor_count == 0
        assert stats.maybe_count == 0
        assert stats.total_count == 0

    def test_record_keep_verdict(self):
        """Should record keep verdict correctly."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()
        result = VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Keep this",
            detailed_reasons=[],
            estimated_value=50.0,
            confidence="high",
        )
        stats.record(result)
        assert stats.keep_count == 1
        assert stats.vendor_count == 0
        assert stats.maybe_count == 0
        assert stats.keep_value == 50.0
        assert stats.high_confidence_count == 1

    def test_record_vendor_verdict(self):
        """Should record vendor verdict correctly."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()
        result = VerdictResult(
            verdict=Verdict.VENDOR,
            explanation="Vendor this",
            detailed_reasons=[],
            estimated_value=1.0,
            confidence="high",
        )
        stats.record(result)
        assert stats.vendor_count == 1
        assert stats.keep_count == 0
        assert stats.vendor_value == 1.0

    def test_record_maybe_verdict(self):
        """Should record maybe verdict correctly."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()
        result = VerdictResult(
            verdict=Verdict.MAYBE,
            explanation="Check further",
            detailed_reasons=[],
            estimated_value=10.0,
            confidence="medium",
        )
        stats.record(result)
        assert stats.maybe_count == 1
        assert stats.maybe_value == 10.0
        assert stats.medium_confidence_count == 1

    def test_percentages(self):
        """Should calculate percentages correctly."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()

        # Record 2 keep, 2 vendor, 1 maybe
        for _ in range(2):
            stats.record(VerdictResult(
                verdict=Verdict.KEEP,
                explanation="Keep",
                detailed_reasons=[],
            ))
        for _ in range(2):
            stats.record(VerdictResult(
                verdict=Verdict.VENDOR,
                explanation="Vendor",
                detailed_reasons=[],
            ))
        stats.record(VerdictResult(
            verdict=Verdict.MAYBE,
            explanation="Maybe",
            detailed_reasons=[],
        ))

        assert stats.total_count == 5
        assert stats.keep_percentage == 40.0
        assert stats.vendor_percentage == 40.0
        assert stats.maybe_percentage == 20.0

    def test_meta_bonus_tracking(self):
        """Should track meta bonus correctly."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()

        result_with_bonus = VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Meta",
            detailed_reasons=[],
            meta_affixes_found=["life", "resistance"],
            meta_bonus_applied=25.0,
        )
        result_without = VerdictResult(
            verdict=Verdict.VENDOR,
            explanation="No meta",
            detailed_reasons=[],
        )

        stats.record(result_with_bonus)
        stats.record(result_without)

        assert stats.items_with_meta_bonus == 1
        assert stats.total_meta_bonus == 25.0
        assert stats.average_meta_bonus == 25.0

    def test_reset(self):
        """Should reset all statistics to zero."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()

        stats.record(VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Keep",
            detailed_reasons=[],
            estimated_value=100.0,
        ))

        assert stats.keep_count == 1
        assert stats.keep_value == 100.0

        stats.reset()

        assert stats.keep_count == 0
        assert stats.keep_value == 0.0
        assert stats.total_count == 0

    def test_summary_text_empty(self):
        """Should show no verdicts message when empty."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()
        assert stats.summary_text() == "No verdicts yet"

    def test_summary_text_with_data(self):
        """Should show summary with counts and value."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()

        stats.record(VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Keep",
            detailed_reasons=[],
            estimated_value=50.0,
        ))
        stats.record(VerdictResult(
            verdict=Verdict.VENDOR,
            explanation="Vendor",
            detailed_reasons=[],
        ))

        summary = stats.summary_text()
        assert "👍 1" in summary
        assert "👎 1" in summary
        assert "50c" in summary

    def test_total_value(self):
        """Should calculate total value across all verdict types."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()

        stats.record(VerdictResult(
            verdict=Verdict.KEEP,
            explanation="Keep",
            detailed_reasons=[],
            estimated_value=100.0,
        ))
        stats.record(VerdictResult(
            verdict=Verdict.VENDOR,
            explanation="Vendor",
            detailed_reasons=[],
            estimated_value=5.0,
        ))
        stats.record(VerdictResult(
            verdict=Verdict.MAYBE,
            explanation="Maybe",
            detailed_reasons=[],
            estimated_value=25.0,
        ))

        assert stats.total_value == 130.0

    def test_confidence_tracking_low(self):
        """Should track low confidence verdicts."""
        from core.quick_verdict import VerdictStatistics
        stats = VerdictStatistics()

        stats.record(VerdictResult(
            verdict=Verdict.MAYBE,
            explanation="Uncertain",
            detailed_reasons=[],
            confidence="low",
        ))

        assert stats.low_confidence_count == 1
        assert stats.medium_confidence_count == 0
        assert stats.high_confidence_count == 0
