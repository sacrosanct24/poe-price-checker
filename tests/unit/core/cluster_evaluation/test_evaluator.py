"""
Tests for ClusterJewelEvaluator.

Tests cluster jewel evaluation including:
- Excellent tier (meta notables + synergies)
- Good tier (high-tier notables)
- Vendor tier (low-tier notables)
- Non-cluster jewels returning None
"""

from __future__ import annotations

import pytest

from core.item_parser import ParsedItem
from core.cluster_evaluation import (
    ClusterJewelEvaluator,
    ClusterJewelEvaluation,
    NotableMatch,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def evaluator():
    """Create a ClusterJewelEvaluator instance."""
    return ClusterJewelEvaluator()


class TestClusterJewelDetection:
    """Tests for is_cluster_jewel detection."""

    def test_detects_large_cluster_jewel(self, evaluator):
        """Large cluster jewel should be detected."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
        )
        assert evaluator.is_cluster_jewel(item) is True

    def test_detects_medium_cluster_jewel(self, evaluator):
        """Medium cluster jewel should be detected."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Medium Cluster Jewel",
        )
        assert evaluator.is_cluster_jewel(item) is True

    def test_detects_small_cluster_jewel(self, evaluator):
        """Small cluster jewel should be detected."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Small Cluster Jewel",
        )
        assert evaluator.is_cluster_jewel(item) is True

    def test_non_cluster_jewel_not_detected(self, evaluator):
        """Regular jewel should not be detected as cluster."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            base_type="Prismatic Jewel",
        )
        assert evaluator.is_cluster_jewel(item) is False

    def test_non_jewel_not_detected(self, evaluator):
        """Non-jewel item should not be detected as cluster."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Vaal Regalia",
        )
        assert evaluator.is_cluster_jewel(item) is False


class TestExcellentClusterEvaluation:
    """Tests for excellent tier cluster jewels."""

    def test_evaluates_excellent_with_meta_notables_and_synergy(self, evaluator):
        """Meta notables with synergy should evaluate to excellent."""
        item = ParsedItem(
            raw_text="Test cluster",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            item_level=84,
            cluster_jewel_size="Large",
            cluster_jewel_passives=8,
            cluster_jewel_enchantment="fire_damage",
            cluster_jewel_notables=["Blowback", "Fan the Flames", "Burning Bright"],
            cluster_jewel_sockets=1,
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert isinstance(result, ClusterJewelEvaluation)
        assert result.tier == "excellent"
        assert result.total_score >= 80
        assert len(result.synergies_found) > 0
        assert "2-10div" in result.estimated_value or "5-20div" in result.estimated_value

    def test_large_cluster_with_two_sockets_higher_value(self, evaluator):
        """Large cluster with 2 sockets should have higher value estimate."""
        item = ParsedItem(
            raw_text="Test cluster",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            item_level=84,
            cluster_jewel_size="Large",
            cluster_jewel_passives=12,
            cluster_jewel_enchantment="fire_damage",
            cluster_jewel_notables=["Blowback", "Fan the Flames"],
            cluster_jewel_sockets=2,
        )

        result = evaluator.evaluate(item)

        assert result is not None
        # 2 sockets on large cluster is premium
        assert result.tier in ["excellent", "good"]


class TestGoodClusterEvaluation:
    """Tests for good tier cluster jewels."""

    def test_evaluates_good_with_high_tier_notables(self, evaluator):
        """High-tier notables without synergy should evaluate to good."""
        item = ParsedItem(
            raw_text="Test cluster",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            item_level=75,
            cluster_jewel_size="Large",
            cluster_jewel_passives=8,
            cluster_jewel_enchantment="attack_damage",
            cluster_jewel_notables=["Feed the Fury"],
            cluster_jewel_sockets=1,
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert result.tier in ["good", "excellent"]
        assert len(result.matched_notables) >= 1


class TestAverageClusterEvaluation:
    """Tests for average tier cluster jewels."""

    def test_evaluates_average_with_medium_notables(self, evaluator):
        """Medium-tier notables should evaluate to average."""
        item = ParsedItem(
            raw_text="Test cluster",
            rarity="RARE",
            base_type="Medium Cluster Jewel",
            item_level=68,
            cluster_jewel_size="Medium",
            cluster_jewel_passives=5,
            cluster_jewel_enchantment="unknown_type",
            cluster_jewel_notables=["SomeUnknownNotable"],
            cluster_jewel_sockets=0,
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert result.tier in ["average", "vendor"]


class TestVendorClusterEvaluation:
    """Tests for vendor tier cluster jewels."""

    def test_evaluates_vendor_with_no_notables(self, evaluator):
        """Cluster with no notables should evaluate to vendor."""
        item = ParsedItem(
            raw_text="Test cluster",
            rarity="RARE",
            base_type="Small Cluster Jewel",
            item_level=50,
            cluster_jewel_size="Small",
            cluster_jewel_passives=2,
            cluster_jewel_enchantment="unknown",
            cluster_jewel_notables=[],
            cluster_jewel_sockets=0,
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert result.tier == "vendor"
        assert result.estimated_value == "<10c"


class TestNonClusterReturnsNone:
    """Tests that non-cluster jewels return None."""

    def test_non_cluster_returns_none(self, evaluator):
        """Non-cluster jewel should return None from evaluate."""
        item = ParsedItem(
            raw_text="Test",
            rarity="UNIQUE",
            base_type="Prismatic Jewel",
        )

        result = evaluator.evaluate(item)

        assert result is None

    def test_rare_armor_returns_none(self, evaluator):
        """Rare armor should return None from evaluate."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Vaal Regalia",
        )

        result = evaluator.evaluate(item)

        assert result is None


class TestNotableMatching:
    """Tests for notable matching functionality."""

    def test_matches_known_notable(self, evaluator):
        """Known notables should be matched with proper tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            cluster_jewel_size="Large",
            cluster_jewel_notables=["Sadist"],  # Meta tier notable
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert len(result.matched_notables) == 1
        notable = result.matched_notables[0]
        assert notable.name == "Sadist"
        assert notable.tier == "meta"
        assert notable.weight == 10

    def test_unknown_notable_gets_default_values(self, evaluator):
        """Unknown notables should get default medium tier."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            cluster_jewel_size="Large",
            cluster_jewel_notables=["SomeNewNotableNotInDatabase"],
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert len(result.matched_notables) == 1
        notable = result.matched_notables[0]
        assert notable.name == "SomeNewNotableNotInDatabase"
        assert notable.tier == "medium"
        assert notable.weight == 5


class TestSynergyDetection:
    """Tests for synergy detection between notables."""

    def test_detects_fire_dot_synergy(self, evaluator):
        """Fire DoT synergy should be detected."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            cluster_jewel_size="Large",
            cluster_jewel_notables=["Blowback", "Fan the Flames"],
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert len(result.synergies_found) > 0
        assert result.synergy_bonus > 0

    def test_no_synergy_when_notables_dont_match(self, evaluator):
        """No synergy should be detected when notables don't form a combo."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            cluster_jewel_size="Large",
            cluster_jewel_notables=["Blowback"],  # Only one of the combo
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert len(result.synergies_found) == 0


class TestIlvlScoring:
    """Tests for item level scoring."""

    def test_high_ilvl_gives_bonus(self, evaluator):
        """High ilvl should give crafting bonus."""
        item_high = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            item_level=84,
            cluster_jewel_size="Large",
            cluster_jewel_notables=["Blowback"],
        )

        item_low = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            item_level=50,
            cluster_jewel_size="Large",
            cluster_jewel_notables=["Blowback"],
        )

        result_high = evaluator.evaluate(item_high)
        result_low = evaluator.evaluate(item_low)

        assert result_high is not None
        assert result_low is not None
        assert result_high.ilvl_score > result_low.ilvl_score


class TestEnchantmentScoring:
    """Tests for enchantment type scoring."""

    def test_popular_enchant_gives_high_score(self, evaluator):
        """Popular enchantment types should score higher."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            cluster_jewel_size="Large",
            cluster_jewel_enchantment="minion_damage",  # Popular enchant
            cluster_jewel_notables=["Rotten Claws"],
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert result.enchantment_score >= 50


class TestFactorsGeneration:
    """Tests for human-readable factors list."""

    def test_generates_factors_for_high_score_cluster(self, evaluator):
        """High-scoring cluster should have multiple factors."""
        item = ParsedItem(
            raw_text="Test",
            rarity="RARE",
            base_type="Large Cluster Jewel",
            item_level=84,
            cluster_jewel_size="Large",
            cluster_jewel_passives=8,
            cluster_jewel_enchantment="fire_damage",
            cluster_jewel_notables=["Blowback", "Fan the Flames"],
            cluster_jewel_sockets=1,
        )

        result = evaluator.evaluate(item)

        assert result is not None
        assert len(result.factors) > 0
        # Should mention synergy, notables, ilvl, or sockets
        factors_text = " ".join(result.factors).lower()
        assert any(word in factors_text for word in ["synergy", "notable", "ilvl", "socket", "enchantment"])
