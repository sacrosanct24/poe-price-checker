"""
Unit tests for core.rare_item_evaluator module - Rare item evaluation logic.

Tests cover:
- Base type evaluation
- Item level checking
- Affix matching with tier detection
- Influence mod detection
- Synergy detection
- Red flag detection
- Score calculation
- Tier determination
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from core.rare_item_evaluator import (
    RareItemEvaluator,
    AffixMatch,
    RareItemEvaluation
)
from core.item_parser import ParsedItem

pytestmark = pytest.mark.unit


# -------------------------
# Fixtures
# -------------------------

@pytest.fixture
def mock_data_dir(tmp_path):
    """Create temporary data directory with test configurations."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create valuable_affixes.json
    affixes = {
        "life": {
            "tier1": ["+# to maximum Life"],
            "tier2": ["+# to maximum Life"],
            "tier3": ["+# to maximum Life"],
            "tier1_range": [100, 109],
            "tier2_range": [90, 99],
            "tier3_range": [80, 89],
            "weight": 10,
            "tier2_weight": 8,
            "tier3_weight": 6,
            "min_value": 70
        },
        "resistances": {
            "tier1": [
                "+#% to Fire Resistance",
                "+#% to Cold Resistance",
                "+#% to Lightning Resistance"
            ],
            "tier2": [
                "+#% to Fire Resistance",
                "+#% to Cold Resistance",
                "+#% to Lightning Resistance"
            ],
            "tier3": [
                "+#% to Fire Resistance",
                "+#% to Cold Resistance",
                "+#% to Lightning Resistance"
            ],
            "tier1_range": [46, 48],
            "tier2_range": [42, 45],
            "tier3_range": [36, 41],
            "weight": 8,
            "tier2_weight": 7,
            "tier3_weight": 5,
            "min_value": 35
        },
        "energy_shield": {
            "tier1": ["+# to maximum Energy Shield"],
            "tier2": ["+# to maximum Energy Shield"],
            "tier3": ["+# to maximum Energy Shield"],
            "tier1_range": [80, 110],
            "tier2_range": [60, 79],
            "tier3_range": [45, 59],
            "weight": 9,
            "tier2_weight": 7,
            "tier3_weight": 5,
            "min_value": 40
        },
        "movement_speed": {
            "tier1": ["#% increased Movement Speed"],
            "weight": 9,
            "min_value": 25
        },
        "_synergies": {
            "life_and_res": {
                "required": {"life": 1, "resistances": 2},
                "bonus_score": 10,
                "description": "Life + Multiple Resistances"
            }
        },
        "_red_flags": {
            "life_and_es": {
                "check": "has_both",
                "affixes": ["life", "energy_shield"],
                "penalty_score": -15,
                "description": "Mixed life and ES (anti-synergy)"
            },
            "boots_no_movespeed": {
                "check": "missing_required",
                "slot": "boots",
                "required_affix": "movement_speed",
                "penalty_score": -10,
                "description": "Boots without movement speed"
            }
        },
        "_influence_mods": {
            "crusader": {
                "high_value": [
                    "+#% to Global Critical Strike Multiplier",
                    "# to maximum Mana"
                ],
                "weight": 10
            },
            "hunter": {
                "high_value": [
                    "Attacks have #% chance to inflict Bleed"
                ],
                "weight": 10
            }
        }
    }

    # Create valuable_bases.json
    bases = {
        "body_armour": {
            "high_tier": ["Vaal Regalia", "Carnal Armour"],
            "min_ilvl": 84
        },
        "helmet": {
            "high_tier": ["Hubris Circlet", "Bone Helmet"],
            "min_ilvl": 84
        },
        "boots": {
            "high_tier": ["Sorcerer Boots", "Two-Toned Boots"],
            "min_ilvl": 84
        }
    }

    with open(data_dir / "valuable_affixes.json", 'w') as f:
        json.dump(affixes, f)

    with open(data_dir / "valuable_bases.json", 'w') as f:
        json.dump(bases, f)

    return data_dir


@pytest.fixture
def evaluator(mock_data_dir):
    """Create evaluator with test data."""
    return RareItemEvaluator(data_dir=mock_data_dir)


def create_rare_item(
    name="Test Item",
    base_type="Hubris Circlet",
    item_level=86,
    explicits=None,
    influences=None
):
    """Helper to create ParsedItem for testing."""
    item = ParsedItem(raw_text="")
    item.name = name
    item.rarity = "RARE"
    item.base_type = base_type
    item.item_level = item_level
    item.explicits = explicits or []
    item.influences = influences or []
    return item


# -------------------------
# Initialization Tests
# -------------------------

class TestRareItemEvaluatorInitialization:
    """Test evaluator initialization and data loading."""

    def test_loads_valuable_affixes(self, evaluator):
        """Should load valuable affixes from data file."""
        assert "life" in evaluator.valuable_affixes
        assert "resistances" in evaluator.valuable_affixes
        assert "energy_shield" in evaluator.valuable_affixes

    def test_loads_valuable_bases(self, evaluator):
        """Should load valuable bases from data file."""
        assert "body_armour" in evaluator.valuable_bases
        assert "helmet" in evaluator.valuable_bases
        assert "Hubris Circlet" in evaluator.valuable_bases["helmet"]["high_tier"]

    def test_loads_synergies(self, evaluator):
        """Should load synergies configuration."""
        assert "life_and_res" in evaluator.synergies
        assert evaluator.synergies["life_and_res"]["bonus_score"] == 10

    def test_loads_red_flags(self, evaluator):
        """Should load red flags configuration."""
        assert "life_and_es" in evaluator.red_flags
        assert evaluator.red_flags["life_and_es"]["penalty_score"] == -15

    def test_loads_influence_mods(self, evaluator):
        """Should load influence mod configuration."""
        assert "crusader" in evaluator.influence_mods
        assert "hunter" in evaluator.influence_mods

    def test_handles_missing_data_files(self, tmp_path):
        """Should handle missing data files gracefully."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        evaluator = RareItemEvaluator(data_dir=empty_dir)

        assert evaluator.valuable_affixes == {}
        assert evaluator.valuable_bases == {}


# -------------------------
# Base Evaluation Tests
# -------------------------

class TestBaseEvaluation:
    """Test base type evaluation."""

    def test_recognizes_valuable_base(self, evaluator):
        """Should recognize high-tier base types."""
        item = create_rare_item(base_type="Hubris Circlet")

        is_valuable, score = evaluator._evaluate_base(item)

        assert is_valuable is True
        assert score == 50

    def test_non_valuable_base_gets_low_score(self, evaluator):
        """Non-valuable bases should get low score."""
        item = create_rare_item(base_type="Iron Hat")

        is_valuable, score = evaluator._evaluate_base(item)

        assert is_valuable is False
        assert score == 10

    def test_handles_missing_base_type(self, evaluator):
        """Should handle items without base type."""
        item = create_rare_item(base_type=None)

        is_valuable, score = evaluator._evaluate_base(item)

        assert is_valuable is False
        assert score == 0


# -------------------------
# Item Level Tests
# -------------------------

class TestItemLevelChecking:
    """Test item level validation."""

    def test_high_ilvl_items_pass(self, evaluator):
        """Items with ilvl 84+ should pass."""
        item = create_rare_item(item_level=86)
        assert evaluator._check_ilvl(item) is True

        item = create_rare_item(item_level=84)
        assert evaluator._check_ilvl(item) is True

    def test_low_ilvl_items_fail(self, evaluator):
        """Items below ilvl 84 should fail."""
        item = create_rare_item(item_level=83)
        assert evaluator._check_ilvl(item) is False

        item = create_rare_item(item_level=50)
        assert evaluator._check_ilvl(item) is False

    def test_handles_missing_ilvl(self, evaluator):
        """Should handle items without ilvl."""
        item = create_rare_item(item_level=None)
        assert not evaluator._check_ilvl(item)  # Returns falsy (None) when no ilvl


# -------------------------
# Affix Matching Tests
# -------------------------

class TestAffixMatching:
    """Test matching affixes against valuable patterns."""

    def test_matches_tier1_life(self, evaluator):
        """Should match tier 1 life roll."""
        item = create_rare_item(explicits=["+105 to maximum Life"])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 1
        assert matches[0].affix_type == "life"
        assert matches[0].value == 105
        assert matches[0].tier == "tier1"
        assert matches[0].weight == 10

    def test_matches_tier2_life(self, evaluator):
        """Should match tier 2 life roll."""
        item = create_rare_item(explicits=["+95 to maximum Life"])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 1
        assert matches[0].tier == "tier2"
        assert matches[0].weight == 8

    def test_matches_tier3_life(self, evaluator):
        """Should match tier 3 life roll."""
        item = create_rare_item(explicits=["+82 to maximum Life"])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 1
        assert matches[0].tier == "tier3"
        assert matches[0].weight == 6

    def test_ignores_life_below_minimum(self, evaluator):
        """Should ignore life rolls below minimum value."""
        item = create_rare_item(explicits=["+50 to maximum Life"])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 0

    def test_matches_multiple_resistances(self, evaluator):
        """Should match multiple resistance mods."""
        item = create_rare_item(explicits=[
            "+47% to Fire Resistance",
            "+45% to Cold Resistance",
            "+38% to Lightning Resistance"
        ])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 3
        assert all(m.affix_type == "resistances" for m in matches)
        assert matches[0].tier == "tier1"  # 47%
        assert matches[1].tier == "tier2"  # 45%
        assert matches[2].tier == "tier3"  # 38%

    def test_matches_energy_shield(self, evaluator):
        """Should match energy shield mods."""
        item = create_rare_item(explicits=["+85 to maximum Energy Shield"])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 1
        assert matches[0].affix_type == "energy_shield"
        assert matches[0].value == 85
        assert matches[0].tier == "tier1"

    def test_case_insensitive_matching(self, evaluator):
        """Matching should be case insensitive."""
        item = create_rare_item(explicits=["+100 TO MAXIMUM LIFE"])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 1

    def test_no_matches_for_non_valuable_affixes(self, evaluator):
        """Should not match non-valuable affixes."""
        item = create_rare_item(explicits=[
            "+5 to Strength",
            "+10 to Dexterity"
        ])

        matches = evaluator._match_affixes(item)

        assert len(matches) == 0


# -------------------------
# Influence Mod Tests
# -------------------------

class TestInfluenceModMatching:
    """Test matching influence-specific mods."""

    def test_matches_crusader_influence_mod(self, evaluator):
        """Should match Crusader influence mods."""
        item = create_rare_item(
            explicits=["+35% to Global Critical Strike Multiplier"],
            influences=["Crusader"]
        )

        matches = evaluator._match_affixes(item)

        assert len(matches) == 1
        assert matches[0].affix_type == "crusader_mod"
        assert matches[0].is_influence_mod is True
        assert matches[0].tier == "influence"
        assert matches[0].weight == 10

    def test_matches_hunter_influence_mod(self, evaluator):
        """Should match Hunter influence mods."""
        item = create_rare_item(
            explicits=["Attacks have 25% chance to inflict Bleed"],
            influences=["Hunter"]
        )

        matches = evaluator._match_affixes(item)

        assert len(matches) == 1
        assert matches[0].affix_type == "hunter_mod"
        assert matches[0].is_influence_mod is True

    def test_ignores_influence_mods_without_influence(self, evaluator):
        """Should not match influence mods if item has no influence."""
        item = create_rare_item(
            explicits=["+35% to Global Critical Strike Multiplier"],
            influences=[]
        )

        matches = evaluator._match_affixes(item)

        # Should not match as influence mod (might match as regular affix if defined)
        influence_matches = [m for m in matches if m.is_influence_mod]
        assert len(influence_matches) == 0

    def test_combines_regular_and_influence_mods(self, evaluator):
        """Should match both regular and influence mods."""
        item = create_rare_item(
            explicits=[
                "+100 to maximum Life",
                "+35% to Global Critical Strike Multiplier"
            ],
            influences=["Crusader"]
        )

        matches = evaluator._match_affixes(item)

        assert len(matches) == 2
        regular_matches = [m for m in matches if not m.is_influence_mod]
        influence_matches = [m for m in matches if m.is_influence_mod]
        assert len(regular_matches) == 1
        assert len(influence_matches) == 1


# -------------------------
# Synergy Detection Tests
# -------------------------

class TestSynergyDetection:
    """Test synergy detection between affixes."""

    def test_detects_life_and_res_synergy(self, evaluator):
        """Should detect life + multiple resistances synergy."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
            AffixMatch("resistances", "", "", 45, 7, "tier2", False)
        ]

        synergies, bonus = evaluator._check_synergies(matches)

        assert "life_and_res" in synergies
        assert bonus == 10

    def test_no_synergy_without_requirements(self, evaluator):
        """Should not detect synergy without all requirements."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False)
            # Missing second resistance
        ]

        synergies, bonus = evaluator._check_synergies(matches)

        assert "life_and_res" not in synergies
        assert bonus == 0

    def test_no_synergies_with_empty_matches(self, evaluator):
        """Should handle empty match list."""
        synergies, bonus = evaluator._check_synergies([])

        assert synergies == []
        assert bonus == 0


# -------------------------
# Red Flag Detection Tests
# -------------------------

class TestRedFlagDetection:
    """Test red flag (anti-synergy) detection."""

    def test_detects_life_and_es_anti_synergy(self, evaluator):
        """Should detect life + ES anti-synergy."""
        item = create_rare_item()
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("energy_shield", "", "", 80, 9, "tier1", False)
        ]

        flags, penalty = evaluator._check_red_flags(item, matches)

        assert "life_and_es" in flags
        assert penalty == -15

    def test_detects_boots_without_movespeed(self, evaluator):
        """Should detect boots without movement speed."""
        item = create_rare_item(base_type="Sorcerer Boots")
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False)
            # No movement speed
        ]

        flags, penalty = evaluator._check_red_flags(item, matches)

        assert "boots_no_movespeed" in flags
        assert penalty == -10

    def test_no_red_flag_for_boots_with_movespeed(self, evaluator):
        """Should not flag boots that have movement speed."""
        item = create_rare_item(base_type="Sorcerer Boots")
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("movement_speed", "", "", 30, 9, "tier1", False)
        ]

        flags, penalty = evaluator._check_red_flags(item, matches)

        assert "boots_no_movespeed" not in flags

    def test_no_red_flags_with_good_item(self, evaluator):
        """Should have no red flags for well-rolled item."""
        item = create_rare_item()
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False)
        ]

        flags, penalty = evaluator._check_red_flags(item, matches)

        assert flags == []
        assert penalty == 0


# -------------------------
# Item Slot Detection Tests
# -------------------------

class TestItemSlotDetection:
    """Test determining item equipment slot."""

    def test_detects_boots_slot(self, evaluator):
        """Should detect boots from base type."""
        item = create_rare_item(base_type="Sorcerer Boots")
        assert evaluator._determine_item_slot(item) == "boots"

        item = create_rare_item(base_type="Iron Greaves")
        assert evaluator._determine_item_slot(item) == "boots"

    def test_detects_helmet_slot(self, evaluator):
        """Should detect helmets from base type."""
        item = create_rare_item(base_type="Hubris Circlet")
        assert evaluator._determine_item_slot(item) == "helmet"

        item = create_rare_item(base_type="Bone Helmet")
        assert evaluator._determine_item_slot(item) == "helmet"

        item = create_rare_item(base_type="Blizzard Crown")
        assert evaluator._determine_item_slot(item) == "helmet"

    def test_detects_gloves_slot(self, evaluator):
        """Should detect gloves from base type."""
        item = create_rare_item(base_type="Sorcerer Gloves")
        assert evaluator._determine_item_slot(item) == "gloves"

        item = create_rare_item(base_type="Titan Gauntlets")
        assert evaluator._determine_item_slot(item) == "gloves"

    def test_handles_unknown_slot(self, evaluator):
        """Should return None for unknown base types."""
        item = create_rare_item(base_type="Unknown Item")
        assert evaluator._determine_item_slot(item) is None


# -------------------------
# Score Calculation Tests
# -------------------------

class TestScoreCalculation:
    """Test total score calculation."""

    def test_calculates_total_score(self, evaluator):
        """Should calculate weighted total score."""
        # base: 50, affixes: 80, high_ilvl: yes (10 pts)
        score = evaluator._calculate_total_score(
            base_score=50,
            affix_score=80,
            has_high_ilvl=True,
            synergy_bonus=0,
            red_flag_penalty=0
        )

        # (50 * 0.3) + (80 * 0.6) + 10 = 15 + 48 + 10 = 73
        assert score == 73

    def test_score_with_synergy_bonus(self, evaluator):
        """Should add synergy bonus to score."""
        score = evaluator._calculate_total_score(
            base_score=50,
            affix_score=80,
            has_high_ilvl=True,
            synergy_bonus=10,
            red_flag_penalty=0
        )

        assert score == 83  # 73 + 10

    def test_score_with_red_flag_penalty(self, evaluator):
        """Should subtract red flag penalty from score."""
        score = evaluator._calculate_total_score(
            base_score=50,
            affix_score=80,
            has_high_ilvl=True,
            synergy_bonus=0,
            red_flag_penalty=-15
        )

        assert score == 58  # 73 - 15

    def test_score_caps_at_100(self, evaluator):
        """Score should not exceed 100."""
        score = evaluator._calculate_total_score(
            base_score=50,
            affix_score=100,
            has_high_ilvl=True,
            synergy_bonus=50,
            red_flag_penalty=0
        )

        assert score == 100

    def test_score_floors_at_0(self, evaluator):
        """Score should not go below 0."""
        score = evaluator._calculate_total_score(
            base_score=10,
            affix_score=20,
            has_high_ilvl=False,
            synergy_bonus=0,
            red_flag_penalty=-100
        )

        assert score == 0


# -------------------------
# Tier Determination Tests
# -------------------------

class TestTierDetermination:
    """Test item tier and value estimation."""

    def test_excellent_tier_with_high_score_and_t1_mods(self, evaluator):
        """High score + T1 mods = excellent tier."""
        matches = [
            AffixMatch("life", "", "", 105, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
            AffixMatch("resistances", "", "", 46, 8, "tier1", False)
        ]

        tier, value = evaluator._determine_tier(
            total_score=85,
            matches=matches,
            synergies=[]
        )

        assert tier == "excellent"
        assert "div" in value.lower() or "200c" in value

    def test_good_tier_with_moderate_score(self, evaluator):
        """Moderate score + good affixes = good tier."""
        matches = [
            AffixMatch("life", "", "", 95, 8, "tier2", False),
            AffixMatch("resistances", "", "", 44, 7, "tier2", False)
        ]

        tier, value = evaluator._determine_tier(
            total_score=65,
            matches=matches,
            synergies=["life_and_res"]
        )

        assert tier == "good"

    def test_average_tier_with_low_score(self, evaluator):
        """Lower score = average tier."""
        matches = [
            AffixMatch("life", "", "", 85, 6, "tier3", False)
        ]

        tier, value = evaluator._determine_tier(
            total_score=45,
            matches=matches,
            synergies=[]
        )

        assert tier == "average"

    def test_vendor_tier_with_very_low_score(self, evaluator):
        """Very low score = vendor tier."""
        tier, value = evaluator._determine_tier(
            total_score=20,
            matches=[],
            synergies=[]
        )

        assert tier == "vendor"


# -------------------------
# Full Evaluation Tests
# -------------------------

class TestFullEvaluation:
    """Test complete item evaluation workflow."""

    def test_evaluates_excellent_rare_item(self, evaluator):
        """Should correctly evaluate excellent rare item."""
        item = create_rare_item(
            base_type="Hubris Circlet",
            item_level=86,
            explicits=[
                "+105 to maximum Life",
                "+47% to Fire Resistance",
                "+45% to Cold Resistance",
                "+85 to maximum Energy Shield"
            ]
        )

        eval_result = evaluator.evaluate(item)

        assert eval_result.is_valuable_base is True
        assert eval_result.has_high_ilvl is True
        assert len(eval_result.matched_affixes) == 4
        assert eval_result.total_score >= 60
        assert eval_result.tier in ["good", "excellent"]

    def test_evaluates_vendor_trash(self, evaluator):
        """Should correctly identify vendor trash."""
        item = create_rare_item(
            base_type="Iron Hat",
            item_level=45,
            explicits=[
                "+5 to Strength",
                "+10 to Dexterity"
            ]
        )

        eval_result = evaluator.evaluate(item)

        assert eval_result.is_valuable_base is False
        assert eval_result.has_high_ilvl is False
        assert len(eval_result.matched_affixes) == 0
        assert eval_result.tier == "vendor"

    def test_returns_not_rare_for_non_rare_items(self, evaluator):
        """Should reject non-rare items."""
        item = create_rare_item()
        item.rarity = "UNIQUE"

        eval_result = evaluator.evaluate(item)

        assert eval_result.tier == "not_rare"
        assert eval_result.total_score == 0

    def test_evaluation_includes_synergy_bonus(self, evaluator):
        """Evaluation should include synergy bonuses."""
        item = create_rare_item(
            explicits=[
                "+100 to maximum Life",
                "+47% to Fire Resistance",
                "+45% to Cold Resistance"
            ]
        )

        eval_result = evaluator.evaluate(item)

        assert len(eval_result.synergies_found) > 0
        assert eval_result.synergy_bonus > 0

    def test_evaluation_includes_red_flag_penalty(self, evaluator):
        """Evaluation should include red flag penalties."""
        item = create_rare_item(
            explicits=[
                "+100 to maximum Life",
                "+80 to maximum Energy Shield"
            ]
        )

        eval_result = evaluator.evaluate(item)

        assert len(eval_result.red_flags_found) > 0
        assert eval_result.red_flag_penalty < 0


# -------------------------
# Summary Generation Tests
# -------------------------

class TestSummaryGeneration:
    """Test human-readable summary generation."""

    def test_generates_summary_for_good_item(self, evaluator):
        """Should generate readable summary."""
        item = create_rare_item(
            name="Doom Visor",
            base_type="Hubris Circlet",
            item_level=86,
            explicits=["+100 to maximum Life"]
        )

        eval_result = evaluator.evaluate(item)
        summary = evaluator.get_summary(eval_result)

        assert "Doom Visor" in summary
        assert "Hubris Circlet" in summary
        assert "86" in summary
        assert "Tier:" in summary
        assert "Total Score:" in summary

    def test_summary_includes_matched_affixes(self, evaluator):
        """Summary should list matched affixes."""
        item = create_rare_item(
            explicits=["+100 to maximum Life", "+47% to Fire Resistance"]
        )

        eval_result = evaluator.evaluate(item)
        summary = evaluator.get_summary(eval_result)

        assert "life" in summary.lower()
        assert "resistance" in summary.lower()

    def test_summary_includes_influences(self, evaluator):
        """Summary should show influence types."""
        item = create_rare_item(
            explicits=["+35% to Global Critical Strike Multiplier"],
            influences=["Crusader"]
        )

        eval_result = evaluator.evaluate(item)
        summary = evaluator.get_summary(eval_result)

        assert "Crusader" in summary
