"""
Tests for core/unified_verdict.py

Tests the unified verdict engine including:
- PrimaryAction enum
- Component verdict dataclasses
- UnifiedVerdictEngine evaluation
- Slot inference
- Primary action determination
"""
import pytest
from unittest.mock import MagicMock, patch

from core.unified_verdict import (
    PrimaryAction,
    ForYouVerdict,
    ToSellVerdict,
    ToStashVerdict,
    WhyValuable,
    MarketContext,
    UnifiedVerdict,
    UnifiedVerdictEngine,
    get_unified_verdict,
)


class TestPrimaryAction:
    """Tests for PrimaryAction enum."""

    def test_enum_values(self):
        """All expected actions exist."""
        assert PrimaryAction.KEEP.value == "keep"
        assert PrimaryAction.SELL.value == "sell"
        assert PrimaryAction.STASH.value == "stash"
        assert PrimaryAction.VENDOR.value == "vendor"
        assert PrimaryAction.EVALUATE.value == "evaluate"

    def test_enum_members(self):
        """Enum has expected members."""
        assert len(PrimaryAction) == 5


class TestForYouVerdict:
    """Tests for ForYouVerdict dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        verdict = ForYouVerdict()
        assert verdict.is_upgrade is False
        assert verdict.upgrade_slot is None
        assert verdict.improvement_percent == 0.0
        assert verdict.reason == ""
        assert verdict.current_item_value == 0.0
        assert verdict.comparison_notes == []

    def test_upgrade_verdict(self):
        """Upgrade verdict values."""
        verdict = ForYouVerdict(
            is_upgrade=True,
            upgrade_slot="Ring",
            improvement_percent=15.5,
            reason="Better than current ring",
        )
        assert verdict.is_upgrade is True
        assert verdict.upgrade_slot == "Ring"
        assert verdict.improvement_percent == 15.5


class TestToSellVerdict:
    """Tests for ToSellVerdict dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        verdict = ToSellVerdict()
        assert verdict.is_valuable is False
        assert verdict.estimated_price == 0.0
        assert verdict.price_range == ""
        assert verdict.demand_level == "unknown"
        assert verdict.price_confidence == "low"
        assert verdict.price_source == ""
        assert verdict.market_notes == []

    def test_valuable_item(self):
        """Valuable item verdict."""
        verdict = ToSellVerdict(
            is_valuable=True,
            estimated_price=150.0,
            price_range="~1 div",
            demand_level="high",
            price_confidence="high",
        )
        assert verdict.is_valuable is True
        assert verdict.estimated_price == 150.0
        assert verdict.demand_level == "high"


class TestToStashVerdict:
    """Tests for ToStashVerdict dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        verdict = ToStashVerdict()
        assert verdict.should_stash is False
        assert verdict.good_for_builds == []
        assert verdict.build_match_scores == {}
        assert verdict.stash_reason == ""

    def test_stash_for_builds(self):
        """Stash verdict with builds."""
        verdict = ToStashVerdict(
            should_stash=True,
            good_for_builds=["RF Juggernaut", "Boneshatter"],
            build_match_scores={"RF Juggernaut": 90.0, "Boneshatter": 75.0},
            stash_reason="Good for 2 builds",
        )
        assert len(verdict.good_for_builds) == 2
        assert verdict.build_match_scores["RF Juggernaut"] == 90.0


class TestWhyValuable:
    """Tests for WhyValuable dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        why = WhyValuable()
        assert why.factors == []
        assert why.tier1_mods == []
        assert why.synergies == []
        assert why.crafting_potential == ""

    def test_with_factors(self):
        """WhyValuable with factors."""
        why = WhyValuable(
            factors=["T1 Life", "Double resistance"],
            tier1_mods=["T1 life"],
            synergies=["Life + Resist"],
            crafting_potential="1P/2S open",
        )
        assert len(why.factors) == 2
        assert "T1 life" in why.tier1_mods


class TestMarketContext:
    """Tests for MarketContext dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        context = MarketContext()
        assert context.price_trend == ""
        assert context.trend_percent == 0.0
        assert context.similar_listings == []
        assert context.last_sale is None
        assert context.days_to_sell is None

    def test_with_trend(self):
        """MarketContext with trend data."""
        context = MarketContext(
            price_trend="UP",
            trend_percent=12.5,
            similar_listings=["2.5d", "3d", "3.2d"],
            last_sale="2.8d (2 hrs ago)",
        )
        assert context.price_trend == "UP"
        assert context.trend_percent == 12.5
        assert len(context.similar_listings) == 3


class TestUnifiedVerdict:
    """Tests for UnifiedVerdict dataclass."""

    def test_default_values(self):
        """Default values except primary_action."""
        verdict = UnifiedVerdict(primary_action=PrimaryAction.EVALUATE)
        assert verdict.primary_action == PrimaryAction.EVALUATE
        assert verdict.confidence == "medium"
        assert isinstance(verdict.for_you, ForYouVerdict)
        assert isinstance(verdict.to_sell, ToSellVerdict)
        assert isinstance(verdict.to_stash, ToStashVerdict)
        assert isinstance(verdict.why_valuable, WhyValuable)
        assert isinstance(verdict.market_context, MarketContext)

    def test_get_summary_keep(self):
        """Get summary for KEEP verdict."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.KEEP,
            for_you=ForYouVerdict(
                is_upgrade=True,
                upgrade_slot="Ring",
                improvement_percent=15.0,
            ),
        )
        summary = verdict.get_summary()
        assert "VERDICT: KEEP" in summary
        assert "FOR YOU:  [OK] Upgrade for Ring" in summary
        assert "+15% improvement" in summary

    def test_get_summary_sell(self):
        """Get summary for SELL verdict."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            to_sell=ToSellVerdict(
                is_valuable=True,
                price_range="~50c",
                demand_level="high",
            ),
        )
        summary = verdict.get_summary()
        assert "VERDICT: SELL" in summary
        assert "TO SELL:  [OK] Worth ~50c" in summary
        assert "Demand: high" in summary

    def test_get_summary_stash(self):
        """Get summary for STASH verdict."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.STASH,
            to_stash=ToStashVerdict(
                should_stash=True,
                good_for_builds=["RF Juggernaut", "Boneshatter"],
            ),
        )
        summary = verdict.get_summary()
        assert "VERDICT: STASH" in summary
        assert "TO STASH: [!] Good for:" in summary
        assert "RF Juggernaut" in summary

    def test_get_summary_with_why_valuable(self):
        """Get summary includes WHY VALUABLE."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            why_valuable=WhyValuable(
                factors=["T1 Life", "Triple resistance"],
            ),
        )
        summary = verdict.get_summary()
        assert "WHY VALUABLE:" in summary
        assert "T1 Life" in summary

    def test_get_summary_with_builds(self):
        """Get summary includes BUILDS THAT WANT THIS."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            top_build_matches=["RF Juggernaut (92%)", "Boneshatter (85%)"],
        )
        summary = verdict.get_summary()
        assert "BUILDS THAT WANT THIS:" in summary
        assert "RF Juggernaut (92%)" in summary

    def test_get_summary_with_market_context(self):
        """Get summary includes MARKET CONTEXT."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            market_context=MarketContext(
                price_trend="UP",
                trend_percent=10.0,
                similar_listings=["2d", "2.5d"],
            ),
        )
        summary = verdict.get_summary()
        assert "MARKET CONTEXT:" in summary
        assert "Trending UP" in summary
        assert "+10%" in summary

    def test_get_action_text_keep(self):
        """Get action text for KEEP."""
        verdict = UnifiedVerdict(primary_action=PrimaryAction.KEEP)
        assert "KEEP" in verdict.get_action_text()

    def test_get_action_text_sell(self):
        """Get action text for SELL."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.SELL,
            to_sell=ToSellVerdict(price_range="~50c"),
        )
        text = verdict.get_action_text()
        assert "SELL" in text
        assert "~50c" in text

    def test_get_action_text_stash(self):
        """Get action text for STASH."""
        verdict = UnifiedVerdict(
            primary_action=PrimaryAction.STASH,
            to_stash=ToStashVerdict(good_for_builds=["RF"]),
        )
        text = verdict.get_action_text()
        assert "STASH" in text
        assert "RF" in text

    def test_get_action_text_vendor(self):
        """Get action text for VENDOR."""
        verdict = UnifiedVerdict(primary_action=PrimaryAction.VENDOR)
        assert "VENDOR" in verdict.get_action_text()

    def test_get_action_text_evaluate(self):
        """Get action text for EVALUATE."""
        verdict = UnifiedVerdict(primary_action=PrimaryAction.EVALUATE)
        assert "EVALUATE" in verdict.get_action_text()


class TestUnifiedVerdictEngine:
    """Tests for UnifiedVerdictEngine class."""

    def test_initialization(self):
        """Engine initializes with dependencies."""
        mock_qv = MagicMock()
        mock_rare = MagicMock()
        mock_upgrade = MagicMock()

        engine = UnifiedVerdictEngine(
            quick_verdict_calculator=mock_qv,
            rare_evaluator=mock_rare,
            upgrade_finder=mock_upgrade,
        )
        assert engine._quick_verdict == mock_qv
        assert engine._rare_evaluator == mock_rare
        assert engine._upgrade_finder == mock_upgrade

    def test_evaluate_returns_verdict(self):
        """Evaluate returns UnifiedVerdict."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item)

        assert isinstance(verdict, UnifiedVerdict)

    def test_evaluate_with_price_sets_sell_verdict(self):
        """Price affects to_sell verdict."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item, price=100.0)

        assert verdict.to_sell.estimated_price == 100.0
        assert verdict.to_sell.is_valuable is True  # >= 10c threshold

    def test_evaluate_low_price_not_valuable(self):
        """Low price items are not valuable."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item, price=5.0)

        assert verdict.to_sell.is_valuable is False

    def test_price_range_chaos(self):
        """Price range formatted as chaos."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item, price=50.0)

        assert verdict.to_sell.price_range == "~50c"

    def test_price_range_divine(self):
        """Price range formatted as divines."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item, price=300.0)

        assert "div" in verdict.to_sell.price_range

    def test_evaluate_with_market_data(self):
        """Market data populates context."""
        item = MagicMock()
        item.rarity = "Normal"

        market_data = {
            "trend": "UP",
            "trend_percent": 15.0,
            "similar_listings": ["1d", "1.2d"],
            "demand": "high",
        }

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item, price=150.0, market_data=market_data)

        assert verdict.market_context.price_trend == "UP"
        assert verdict.market_context.trend_percent == 15.0
        assert verdict.to_sell.demand_level == "high"

    def test_determine_action_upgrade_is_keep(self):
        """Upgrade item gets KEEP action."""
        item = MagicMock()
        item.rarity = "Normal"
        item.slot = "Ring"
        item.base_type = "Two-Stone Ring"

        mock_upgrade_finder = MagicMock()
        mock_upgrade_finder.is_upgrade.return_value = True

        user_build = MagicMock()

        engine = UnifiedVerdictEngine(upgrade_finder=mock_upgrade_finder)
        verdict = engine.evaluate(item, user_build=user_build)

        assert verdict.primary_action == PrimaryAction.KEEP
        assert verdict.for_you.is_upgrade is True

    def test_determine_action_valuable_is_sell(self):
        """Valuable non-upgrade gets SELL action."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item, price=100.0)

        assert verdict.primary_action == PrimaryAction.SELL

    def test_determine_action_low_price_vendor(self):
        """Very low price gets VENDOR action."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item, price=1.0)

        assert verdict.primary_action == PrimaryAction.VENDOR

    def test_no_price_evaluate(self):
        """No price gets EVALUATE action."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item)

        assert verdict.primary_action == PrimaryAction.EVALUATE

    def test_no_build_profile_reason(self):
        """No build profile sets reason."""
        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine()
        verdict = engine.evaluate(item)

        assert "No build profile" in verdict.for_you.reason


class TestSlotInference:
    """Tests for slot inference from base type."""

    def test_infer_ring(self):
        """Infer ring slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Two-Stone Ring") == "Ring"
        assert engine._infer_slot("Moonstone Ring") == "Ring"

    def test_infer_amulet(self):
        """Infer amulet slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Onyx Amulet") == "Amulet"
        assert engine._infer_slot("Citrine Amulet") == "Amulet"

    def test_infer_belt(self):
        """Infer belt slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Leather Belt") == "Belt"
        assert engine._infer_slot("Stygian Vise") == "Belt"
        assert engine._infer_slot("Rustic Sash") == "Belt"

    def test_infer_helmet(self):
        """Infer helmet slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Royal Burgonet") == "Helmet"
        assert engine._infer_slot("Eternal Burgonet") == "Helmet"
        assert engine._infer_slot("Great Crown") == "Helmet"

    def test_infer_body_armour(self):
        """Infer body armour slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Astral Plate") == "Body Armour"
        assert engine._infer_slot("Vaal Regalia") == "Body Armour"
        assert engine._infer_slot("Sadist Garb") == "Body Armour"

    def test_infer_gloves(self):
        """Infer gloves slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Titan Gauntlets") == "Gloves"
        assert engine._infer_slot("Sorcerer Gloves") == "Gloves"
        assert engine._infer_slot("Fingerless Silk Gloves") == "Gloves"

    def test_infer_boots(self):
        """Infer boots slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Titan Greaves") == "Boots"
        assert engine._infer_slot("Sorcerer Boots") == "Boots"

    def test_infer_shield(self):
        """Infer shield slot."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Titanium Spirit Shield") == "Shield"
        assert engine._infer_slot("Pinnacle Tower Shield") == "Shield"
        assert engine._infer_slot("War Buckler") == "Shield"

    def test_infer_unknown(self):
        """Unknown base type returns None."""
        engine = UnifiedVerdictEngine()
        assert engine._infer_slot("Unknown Item Type") is None


class TestConvenienceFunction:
    """Tests for get_unified_verdict convenience function."""

    def test_returns_verdict(self):
        """Function returns UnifiedVerdict."""
        item = MagicMock()
        item.rarity = "Normal"

        verdict = get_unified_verdict(item)
        assert isinstance(verdict, UnifiedVerdict)

    def test_with_price(self):
        """Function accepts price."""
        item = MagicMock()
        item.rarity = "Normal"

        verdict = get_unified_verdict(item, price=100.0)
        assert verdict.to_sell.estimated_price == 100.0

    def test_with_build(self):
        """Function accepts user build."""
        item = MagicMock()
        item.rarity = "Normal"

        user_build = MagicMock()
        verdict = get_unified_verdict(item, user_build=user_build)
        assert isinstance(verdict, UnifiedVerdict)


class TestQuickVerdictIntegration:
    """Tests for quick verdict integration."""

    def test_quick_verdict_populates_reasons(self):
        """Quick verdict reasons become WHY factors."""
        mock_qv = MagicMock()
        qv_result = MagicMock()
        qv_result.estimated_value = 50.0
        qv_result.confidence = "high"
        qv_result.detailed_reasons = ["6-link", "Good base"]
        mock_qv.calculate.return_value = qv_result

        item = MagicMock()
        item.rarity = "Normal"

        engine = UnifiedVerdictEngine(quick_verdict_calculator=mock_qv)
        verdict = engine.evaluate(item, price=50.0)

        assert "6-link" in verdict.why_valuable.factors
        assert "Good base" in verdict.why_valuable.factors


class TestRareItemIntegration:
    """Tests for rare item evaluation integration."""

    def test_rare_item_triggers_evaluation(self):
        """Rare items trigger rare evaluator."""
        mock_rare = MagicMock()
        evaluation = MagicMock()
        evaluation.matched_affixes = []
        evaluation.synergies_found = ["Life+Resist"]
        evaluation.open_prefixes = 1
        evaluation.open_suffixes = 2
        evaluation.cross_build_matches = []
        mock_rare.evaluate.return_value = evaluation

        item = MagicMock()
        item.rarity = "Rare"

        engine = UnifiedVerdictEngine(rare_evaluator=mock_rare)
        verdict = engine.evaluate(item)

        mock_rare.evaluate.assert_called_once_with(item)
        assert "Life+Resist synergy" in verdict.why_valuable.factors
        assert "1P/2S open" in verdict.why_valuable.crafting_potential

    def test_non_rare_skips_evaluation(self):
        """Non-rare items skip rare evaluation."""
        mock_rare = MagicMock()

        item = MagicMock()
        item.rarity = "Unique"

        engine = UnifiedVerdictEngine(rare_evaluator=mock_rare)
        engine.evaluate(item)

        mock_rare.evaluate.assert_not_called()

    def test_cross_build_matches_populate_stash(self):
        """Cross-build matches affect stash verdict."""
        mock_rare = MagicMock()
        evaluation = MagicMock()
        evaluation.matched_affixes = []
        evaluation.synergies_found = []
        evaluation.open_prefixes = 0
        evaluation.open_suffixes = 0

        # Create cross-build matches
        match1 = MagicMock()
        match1.archetype = MagicMock()
        match1.archetype.name = "RF Juggernaut"
        match1.score = 92.0

        match2 = MagicMock()
        match2.archetype = MagicMock()
        match2.archetype.name = "Boneshatter"
        match2.score = 85.0

        evaluation.cross_build_matches = [match1, match2]
        mock_rare.evaluate.return_value = evaluation

        item = MagicMock()
        item.rarity = "Rare"

        engine = UnifiedVerdictEngine(rare_evaluator=mock_rare)
        verdict = engine.evaluate(item)

        assert "RF Juggernaut" in verdict.to_stash.good_for_builds
        assert "Boneshatter" in verdict.to_stash.good_for_builds
        assert verdict.to_stash.should_stash is True
