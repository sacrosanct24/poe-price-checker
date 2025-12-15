"""
Tests for UniqueItemEvaluator.

Tests unique item evaluation including:
- Unique item detection
- Chase unique detection
- Corruption evaluation
- Link/socket evaluation
- Meta relevance scoring
- Tier determination
"""

from __future__ import annotations

import pytest

from core.item_parser import ParsedItem
from core.unique_evaluation import (
    UniqueItemEvaluator,
    UniqueItemEvaluation,
    CorruptionMatch,
    LinkEvaluation,
    MetaRelevance,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def evaluator():
    """Create a UniqueItemEvaluator instance."""
    return UniqueItemEvaluator()


class TestUniqueDetection:
    """Tests for is_unique_item detection."""

    def test_detects_unique_item(self, evaluator):
        """Unique item should be detected."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Headhunter",
            base_type="Leather Belt",
        )
        assert evaluator.is_unique_item(item) is True

    def test_detects_unique_case_insensitive(self, evaluator):
        """Detection should be case insensitive."""
        item = ParsedItem(
            raw_text="Test",
            rarity="unique",
            name="Goldrim",
            base_type="Leather Cap",
        )
        assert evaluator.is_unique_item(item) is True

    def test_rare_not_detected_as_unique(self, evaluator):
        """Rare item should not be detected as unique."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            name="Test Rare",
            base_type="Leather Belt",
        )
        assert evaluator.is_unique_item(item) is False

    def test_magic_not_detected_as_unique(self, evaluator):
        """Magic item should not be detected as unique."""
        item = ParsedItem(
            raw_text="Test",
            rarity="MAGIC",
            base_type="Iron Ring",
        )
        assert evaluator.is_unique_item(item) is False


class TestChaseUniqueDetection:
    """Tests for chase unique detection."""

    def test_detects_mageblood_as_chase(self, evaluator):
        """Mageblood should be detected as chase unique."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Mageblood",
            base_type="Heavy Belt",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.is_chase_unique is True
        assert result.tier == "chase"

    def test_detects_headhunter_as_chase(self, evaluator):
        """Headhunter should be detected as chase unique."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Headhunter",
            base_type="Leather Belt",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.is_chase_unique is True
        assert result.tier == "chase"

    def test_regular_unique_not_chase(self, evaluator):
        """Regular unique should not be chase."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Goldrim",
            base_type="Leather Cap",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.is_chase_unique is False


class TestCorruptionEvaluation:
    """Tests for corruption analysis."""

    def test_uncorrupted_item_neutral(self, evaluator):
        """Uncorrupted item should have neutral corruption tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Goldrim",
            base_type="Leather Cap",
            is_corrupted=False,
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.corruption_tier == "none"
        assert result.corruption_value_modifier == 1.0

    def test_excellent_corruption_plus_gems(self, evaluator):
        """Item with +gems corruption should have excellent tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Cloak of Flame",
            base_type="Scholar's Robe",
            is_corrupted=True,
            implicits=["+2 to Level of all Skill Gems"],
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.corruption_tier == "excellent"
        assert result.corruption_value_modifier > 1.0
        assert len(result.corruption_matches) > 0

    def test_good_corruption_crit_chance(self, evaluator):
        """Item with crit corruption should have high tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Test Item",
            base_type="Onyx Amulet",
            is_corrupted=True,
            implicits=["+1% to Critical Strike Chance"],
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.corruption_tier in ["excellent", "high", "good"]
        assert result.corruption_value_modifier >= 1.0

    def test_bricked_corruption(self, evaluator):
        """Bricked corruption should reduce value."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Goldrim",
            base_type="Leather Cap",
            is_corrupted=True,
            implicits=["-30% to Fire Resistance"],
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.corruption_tier == "bricked"
        assert result.corruption_value_modifier < 1.0

    def test_white_socket_bonus(self, evaluator):
        """White sockets should add corruption bonus."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Tabula Rasa",
            base_type="Simple Robe",
            is_corrupted=True,
            sockets="W-W-W-W-W-W",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert any(m.corruption_type == "socket" for m in result.corruption_matches)


class TestLinkEvaluation:
    """Tests for socket/link analysis."""

    def test_six_link_premium(self, evaluator):
        """6-link should have high link multiplier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Carcass Jack",
            base_type="Varnished Coat",
            sockets="R-R-R-G-G-B",
            links=6,
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.link_evaluation is not None
        assert result.link_evaluation.links == 6
        assert result.link_evaluation.link_multiplier >= 2.0

    def test_five_link_multiplier(self, evaluator):
        """5-link should have moderate multiplier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Belly of the Beast",
            base_type="Full Wyrmscale",
            sockets="R-R-R-G-B B",
            links=5,
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.link_evaluation is not None
        assert result.link_evaluation.links == 5
        assert result.link_evaluation.link_multiplier >= 1.0

    def test_no_sockets_no_evaluation(self, evaluator):
        """Item without sockets should have None link evaluation."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Headhunter",
            base_type="Leather Belt",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.link_evaluation is None


class TestMetaRelevance:
    """Tests for build meta scoring."""

    def test_meta_score_baseline(self, evaluator):
        """Unknown uniques should get baseline meta score."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="SomeObscureUnique",
            base_type="Iron Ring",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.meta_relevance is not None
        assert result.meta_relevance.meta_score >= 0


class TestNinjaPrice:
    """Tests for poe.ninja price handling."""

    def test_with_ninja_price(self, evaluator):
        """Item with ninja price should use it."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Test Unique",
            base_type="Iron Ring",
        )
        result = evaluator.evaluate(item, ninja_price=500.0)

        assert result is not None
        assert result.has_poe_ninja_price is True
        assert result.ninja_price_chaos == 500.0
        assert result.confidence == "exact"

    def test_without_ninja_price(self, evaluator):
        """Item without ninja price should estimate."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Test Unique",
            base_type="Iron Ring",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.has_poe_ninja_price is False
        assert result.confidence in ["estimated", "fallback"]


class TestTierDetermination:
    """Tests for final tier assignment."""

    def test_chase_tier_for_chase_uniques(self, evaluator):
        """Chase uniques should get chase tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Mageblood",
            base_type="Heavy Belt",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.tier == "chase"

    def test_excellent_tier_with_high_price(self, evaluator):
        """High price unique should get excellent tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Ashes of the Stars",
            base_type="Onyx Amulet",
        )
        result = evaluator.evaluate(item, ninja_price=1000.0)

        assert result is not None
        assert result.tier in ["chase", "excellent"]

    def test_vendor_tier_low_price(self, evaluator):
        """Low price unique should get low tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Goldrim",
            base_type="Leather Cap",
        )
        result = evaluator.evaluate(item, ninja_price=1.0)

        assert result is not None
        assert result.tier in ["average", "vendor"]


class TestSlotDetection:
    """Tests for slot category detection."""

    def test_detects_belt_slot(self, evaluator):
        """Belt should be detected correctly."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Headhunter",
            base_type="Leather Belt",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.slot_category == "belt"

    def test_detects_body_armour_slot(self, evaluator):
        """Body armour should be detected correctly."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Carcass Jack",
            base_type="Varnished Coat",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.slot_category == "body_armour"

    def test_detects_amulet_slot(self, evaluator):
        """Amulet should be detected correctly."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Ashes of the Stars",
            base_type="Onyx Amulet",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.slot_category == "amulet"

    def test_detects_jewel_slot(self, evaluator):
        """Jewel should be detected correctly."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Watcher's Eye",
            base_type="Prismatic Jewel",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert result.slot_category == "jewel"


class TestFactorsGeneration:
    """Tests for factors/explanation generation."""

    def test_chase_unique_has_factors(self, evaluator):
        """Chase unique should have factors explaining tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Headhunter",
            base_type="Leather Belt",
        )
        result = evaluator.evaluate(item)

        assert result is not None
        assert len(result.factors) > 0
        assert any("Chase" in f or "chase" in f.lower() for f in result.factors)

    def test_priced_unique_has_price_factor(self, evaluator):
        """Priced unique should have price factor."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            name="Test",
            base_type="Onyx Amulet",
        )
        result = evaluator.evaluate(item, ninja_price=500.0)

        assert result is not None
        assert any("price" in f.lower() for f in result.factors)


class TestNonUniqueReturnsNone:
    """Tests that non-unique items return None."""

    def test_rare_returns_none(self, evaluator):
        """Rare item should return None."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Leather Belt",
        )
        result = evaluator.evaluate(item)
        assert result is None

    def test_magic_returns_none(self, evaluator):
        """Magic item should return None."""
        item = ParsedItem(
            raw_text="Test",
            rarity="MAGIC",
            base_type="Iron Ring",
        )
        result = evaluator.evaluate(item)
        assert result is None

    def test_currency_returns_none(self, evaluator):
        """Currency should return None."""
        item = ParsedItem(
            raw_text="Test",
            rarity="Currency",
            base_type="Divine Orb",
        )
        result = evaluator.evaluate(item)
        assert result is None
