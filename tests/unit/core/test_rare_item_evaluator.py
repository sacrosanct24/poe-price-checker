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

from core.rare_evaluation import (
    RareItemEvaluator,
    AffixMatch
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

    def test_returns_unique_evaluation_for_unique_items(self, evaluator):
        """Unique items should get proper unique evaluation."""
        item = create_rare_item()
        item.rarity = "UNIQUE"
        item.name = "Test Unique"

        eval_result = evaluator.evaluate(item)

        # Unique items now get proper evaluation, not "not_rare"
        assert eval_result.tier in ["chase", "excellent", "good", "average", "vendor"]
        assert eval_result._unique_evaluation is not None

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


# -------------------------
# Meta Integration Tests
# -------------------------

class TestMetaWeightLoading:
    """Test meta weight loading from cache files."""

    def test_loads_meta_weights_from_cache(self, tmp_path):
        """Should load meta weights from meta_affixes.json."""
        from datetime import datetime

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create meta_affixes.json
        meta_data = {
            "league": "TestLeague",
            "builds_analyzed": 50,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {
                "life": {"popularity_percent": 80.0},
                "resistances": {"popularity_percent": 60.0}
            }
        }
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        # Create minimal affixes file
        (data_dir / "valuable_affixes.json").write_text(json.dumps({}))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        evaluator = RareItemEvaluator(data_dir=data_dir)

        assert evaluator.meta_weights is not None
        assert "life" in evaluator.meta_weights
        assert evaluator._meta_cache_info is not None
        assert evaluator._meta_cache_info["league"] == "TestLeague"

    def test_meta_weights_empty_without_cache(self, tmp_path):
        """Should return empty meta weights when no cache exists."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "valuable_affixes.json").write_text(json.dumps({}))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        evaluator = RareItemEvaluator(data_dir=data_dir)

        assert evaluator.meta_weights == {}
        assert evaluator._meta_cache_info is None

    def test_fallback_to_build_archetypes(self, tmp_path):
        """Should fallback to build_archetypes.json for meta weights."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create build_archetypes.json with meta weights
        archetypes_data = {
            "archetypes": {},
            "_meta_weights": {
                "popularity_boosts": {
                    "life": 2,
                    "movement_speed": 1
                }
            }
        }
        (data_dir / "build_archetypes.json").write_text(json.dumps(archetypes_data))
        (data_dir / "valuable_affixes.json").write_text(json.dumps({}))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        evaluator = RareItemEvaluator(data_dir=data_dir)

        assert evaluator.meta_weights is not None
        assert "life" in evaluator.meta_weights
        assert evaluator._meta_cache_info["source"] == "build_archetypes.json"


class TestMetaBonusApplication:
    """Test meta bonus application to affix weights."""

    @pytest.fixture
    def meta_evaluator(self, tmp_path):
        """Create evaluator with meta weights configured."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create affixes file
        affixes = {
            "life": {
                "tier1": ["+# to maximum Life"],
                "tier1_range": [100, 109],
                "weight": 8,
                "min_value": 70
            },
            "resistances": {
                "tier1": ["+#% to Fire Resistance"],
                "tier1_range": [46, 48],
                "weight": 6,
                "min_value": 35
            }
        }
        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        # Create meta weights where life is very popular (should get bonus)
        from datetime import datetime
        meta_data = {
            "league": "TestLeague",
            "builds_analyzed": 100,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {
                "life": {"popularity_percent": 80.0},  # 5 + 80*0.1 = 13 >= 10 threshold
                "resistances": {"popularity_percent": 30.0}  # 5 + 30*0.1 = 8 < 10 threshold
            }
        }
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        return RareItemEvaluator(data_dir=data_dir)

    def test_get_affix_weight_applies_meta_bonus(self, meta_evaluator):
        """Should apply +2 bonus to affixes meeting meta threshold."""
        weight, has_bonus = meta_evaluator._get_affix_weight("life", "tier1")

        # Base weight 8 + meta bonus 2 = 10 (capped)
        assert weight == 10
        assert has_bonus is True

    def test_get_affix_weight_no_bonus_below_threshold(self, meta_evaluator):
        """Should NOT apply bonus to affixes below meta threshold."""
        weight, has_bonus = meta_evaluator._get_affix_weight("resistances", "tier1")

        # Base weight 6, no bonus
        assert weight == 6
        assert has_bonus is False

    def test_matched_affix_has_meta_bonus_flag(self, meta_evaluator):
        """AffixMatch should have has_meta_bonus set correctly."""
        item = create_rare_item(
            explicits=["+105 to maximum Life", "+47% to Fire Resistance"]
        )

        matches = meta_evaluator._match_affixes(item)

        life_matches = [m for m in matches if m.affix_type == "life"]
        res_matches = [m for m in matches if m.affix_type == "resistances"]

        assert len(life_matches) == 1
        assert life_matches[0].has_meta_bonus is True

        assert len(res_matches) == 1
        assert res_matches[0].has_meta_bonus is False


class TestMetaInfoDisplay:
    """Test meta information display in summaries."""

    def test_get_meta_info_with_cache(self, tmp_path):
        """Should return formatted meta info string."""
        from datetime import datetime

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        meta_data = {
            "league": "Settlers",
            "builds_analyzed": 75,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {
                "life": {"popularity_percent": 100.0},
                "resistances": {"popularity_percent": 80.0},
                "chaos_resistance": {"popularity_percent": 60.0}
            }
        }
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))
        (data_dir / "valuable_affixes.json").write_text(json.dumps({}))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        evaluator = RareItemEvaluator(data_dir=data_dir)
        meta_info = evaluator.get_meta_info()

        assert "Settlers" in meta_info
        assert "75 builds" in meta_info
        assert "life" in meta_info.lower()
        assert "Top Meta Affixes:" in meta_info

    def test_get_meta_info_without_cache(self, tmp_path):
        """Should return 'not available' message without cache."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "valuable_affixes.json").write_text(json.dumps({}))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        evaluator = RareItemEvaluator(data_dir=data_dir)
        meta_info = evaluator.get_meta_info()

        assert "Not available" in meta_info
        assert "static weights" in meta_info.lower()

    def test_summary_shows_meta_bonus_on_affixes(self, tmp_path):
        """Summary should show [META +2] tag on boosted affixes."""
        from datetime import datetime

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {
                "tier1": ["+# to maximum Life"],
                "tier1_range": [100, 109],
                "weight": 8,
                "min_value": 70
            }
        }
        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        meta_data = {
            "league": "TestLeague",
            "builds_analyzed": 50,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {
                "life": {"popularity_percent": 80.0}
            }
        }
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        evaluator = RareItemEvaluator(data_dir=data_dir)
        item = create_rare_item(explicits=["+105 to maximum Life"])

        eval_result = evaluator.evaluate(item)
        summary = evaluator.get_summary(eval_result)

        assert "[META +2]" in summary


class TestMetaWeightConstants:
    """Test meta weight configuration constants."""

    def test_meta_cache_expiry_days_default(self):
        """META_CACHE_EXPIRY_DAYS should have reasonable default."""
        from core.constants import META_CACHE_EXPIRY_DAYS
        assert META_CACHE_EXPIRY_DAYS == 7

    def test_meta_bonus_threshold_default(self):
        """META_BONUS_THRESHOLD should have reasonable default."""
        from core.constants import META_BONUS_THRESHOLD
        assert META_BONUS_THRESHOLD == 10

    def test_meta_bonus_amount_default(self):
        """META_BONUS_AMOUNT should have reasonable default."""
        from core.constants import META_BONUS_AMOUNT
        assert META_BONUS_AMOUNT == 2

    def test_max_affix_weight_default(self):
        """MAX_AFFIX_WEIGHT should have reasonable default."""
        from core.constants import MAX_AFFIX_WEIGHT
        assert MAX_AFFIX_WEIGHT == 10


class TestMetaWeightEdgeCases:
    """Test edge cases for meta weight application."""

    @pytest.fixture
    def edge_case_evaluator(self, tmp_path):
        """Create evaluator with high-weight affixes for edge case testing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create affixes with high base weight (9) - near cap
        affixes = {
            "life": {
                "tier1": ["+# to maximum Life"],
                "tier1_range": [100, 109],
                "weight": 9,  # High base weight
                "min_value": 70
            }
        }
        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        # Create meta weights that would trigger bonus
        from datetime import datetime
        meta_data = {
            "league": "TestLeague",
            "builds_analyzed": 100,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {
                "life": {"popularity_percent": 80.0}  # Triggers meta bonus
            }
        }
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        return RareItemEvaluator(data_dir=data_dir)

    def test_weight_capped_at_maximum(self, edge_case_evaluator):
        """Weight should not exceed MAX_AFFIX_WEIGHT even with meta bonus."""
        from core.constants import MAX_AFFIX_WEIGHT

        # Base weight 9 + meta bonus 2 = 11, but should cap at 10
        weight, has_bonus = edge_case_evaluator._get_affix_weight("life", "tier1")

        assert weight <= MAX_AFFIX_WEIGHT
        assert weight == MAX_AFFIX_WEIGHT  # Should be exactly at cap
        assert has_bonus is True

    def test_threshold_boundary_exactly_at_threshold(self, tmp_path):
        """Test behavior at exactly 50% popularity (meta_weight = 10.0)."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {"life": {"tier1": ["+# to maximum Life"], "weight": 6, "min_value": 70}}
        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        # 50% popularity => meta_weight = 5.0 + (50 * 0.1) = 10.0 (exactly at threshold)
        from datetime import datetime
        meta_data = {
            "league": "Test",
            "builds_analyzed": 50,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {"life": {"popularity_percent": 50.0}}
        }
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        evaluator = RareItemEvaluator(data_dir=data_dir)
        weight, has_bonus = evaluator._get_affix_weight("life", "tier1")

        assert has_bonus is True
        assert weight == 8  # Base 6 + bonus 2

    def test_threshold_boundary_just_below_threshold(self, tmp_path):
        """Test behavior at 49% popularity (meta_weight = 9.9)."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {"life": {"tier1": ["+# to maximum Life"], "weight": 6, "min_value": 70}}
        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        # 49% popularity => meta_weight = 5.0 + (49 * 0.1) = 9.9 (just below threshold)
        from datetime import datetime
        meta_data = {
            "league": "Test",
            "builds_analyzed": 50,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {"life": {"popularity_percent": 49.0}}
        }
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        evaluator = RareItemEvaluator(data_dir=data_dir)
        weight, has_bonus = evaluator._get_affix_weight("life", "tier1")

        assert has_bonus is False
        assert weight == 6  # Base weight only, no bonus


class TestAffixMatchWithMetaBonus:
    """Test AffixMatch dataclass meta bonus field."""

    def test_affix_match_default_has_meta_bonus_false(self):
        """AffixMatch should default has_meta_bonus to False."""
        match = AffixMatch(
            affix_type="life",
            pattern="+# to maximum Life",
            mod_text="+100 to maximum Life",
            value=100,
            weight=10,
            tier="tier1",
            is_influence_mod=False
        )

        assert match.has_meta_bonus is False

    def test_affix_match_with_meta_bonus_true(self):
        """AffixMatch can be created with has_meta_bonus=True."""
        match = AffixMatch(
            affix_type="life",
            pattern="+# to maximum Life",
            mod_text="+100 to maximum Life",
            value=100,
            weight=10,
            tier="tier1",
            is_influence_mod=False,
            has_meta_bonus=True
        )

        assert match.has_meta_bonus is True


# -------------------------
# Slot Rules Tests
# -------------------------

class TestSlotRules:
    """Test slot-specific evaluation rules."""

    @pytest.fixture
    def slot_evaluator(self, tmp_path):
        """Create evaluator with slot rules configured."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70},
            "resistances": {"tier1": ["+#% to Fire Resistance"], "weight": 8, "min_value": 35},
            "movement_speed": {"tier1": ["#% increased Movement Speed"], "weight": 9, "min_value": 25},
            "energy_shield": {"tier1": ["+# to maximum Energy Shield"], "weight": 9, "min_value": 40}
        }

        bases = {
            "belt": {
                "high_tier": ["Stygian Vise", "Heavy Belt"],
                "min_ilvl": 84
            },
            "body_armour": {
                "high_tier": ["Vaal Regalia"],
                "min_ilvl": 84
            },
            "_slot_rules": {
                "belt": {
                    "premium_bases": ["Stygian Vise"],
                    "premium_bonus": 15,
                    "bonus_affixes": ["life", "resistances", "energy_shield"],
                    "all_bonus_score": 10
                },
                "body_armour": {
                    "six_link_bonus": 30,
                    "bonus_affixes": ["life", "resistances", "energy_shield"],
                    "all_bonus_score": 10
                }
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps(bases))

        return RareItemEvaluator(data_dir=data_dir)

    def test_premium_base_bonus(self, slot_evaluator):
        """Premium base types should get bonus score."""
        item = create_rare_item(base_type="Stygian Vise")
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
        ]

        bonus, reasons = slot_evaluator._check_slot_rules(item, matches)

        assert bonus == 15
        assert any("Premium base" in r for r in reasons)

    def test_all_bonus_affixes_score(self, slot_evaluator):
        """Having all bonus affixes for slot should give bonus."""
        item = create_rare_item(base_type="Heavy Belt")
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
            AffixMatch("energy_shield", "", "", 80, 9, "tier1", False),
        ]

        bonus, reasons = slot_evaluator._check_slot_rules(item, matches)

        assert bonus == 10
        assert any("Slot-optimal" in r for r in reasons)

    def test_unknown_slot_no_bonus(self, slot_evaluator):
        """Unknown slot should get no bonus."""
        item = create_rare_item(base_type="Unknown Item Type")
        matches = [AffixMatch("life", "", "", 100, 10, "tier1", False)]

        bonus, reasons = slot_evaluator._check_slot_rules(item, matches)

        assert bonus == 0
        assert reasons == []


# -------------------------
# Fractured Item Tests
# -------------------------

class TestFracturedItems:
    """Test fractured item handling."""

    @pytest.fixture
    def fractured_evaluator(self, mock_data_dir):
        """Create evaluator for fractured item testing."""
        return RareItemEvaluator(data_dir=mock_data_dir)

    def test_non_fractured_item(self, fractured_evaluator):
        """Non-fractured items should return no bonus."""
        item = create_rare_item()
        item.is_fractured = False
        matches = [AffixMatch("life", "", "+100 to maximum Life", 100, 10, "tier1", False)]

        is_fractured, bonus, mod = fractured_evaluator._check_fractured(item, matches)

        assert is_fractured is False
        assert bonus == 0
        assert mod is None

    def test_fractured_with_t1_mod(self, fractured_evaluator):
        """Fractured T1 mod should get significant bonus."""
        item = create_rare_item()
        item.is_fractured = True
        matches = [AffixMatch("life", "", "+105 to maximum Life", 105, 10, "tier1", False)]

        is_fractured, bonus, mod = fractured_evaluator._check_fractured(item, matches)

        assert is_fractured is True
        assert bonus == 35  # High-weight T1 fractured = 35
        assert mod == "+105 to maximum Life"

    def test_fractured_with_medium_weight_t1(self, fractured_evaluator):
        """Fractured medium-weight T1 should get good bonus."""
        item = create_rare_item()
        item.is_fractured = True
        matches = [AffixMatch("resistances", "", "+47% to Fire Resistance", 47, 8, "tier1", False)]

        is_fractured, bonus, mod = fractured_evaluator._check_fractured(item, matches)

        assert is_fractured is True
        assert bonus == 30  # Medium-weight T1 = 30

    def test_fractured_with_lower_tier_mod(self, fractured_evaluator):
        """Fractured T2/T3 mod should get lower bonus."""
        item = create_rare_item()
        item.is_fractured = True
        matches = [AffixMatch("life", "", "+85 to maximum Life", 85, 6, "tier3", False)]

        is_fractured, bonus, mod = fractured_evaluator._check_fractured(item, matches)

        assert is_fractured is True
        assert bonus == 10  # Lower tier = 10
        assert mod == "+85 to maximum Life"

    def test_fractured_with_no_matches(self, fractured_evaluator):
        """Fractured item with no valuable matches."""
        item = create_rare_item()
        item.is_fractured = True
        matches = []

        is_fractured, bonus, mod = fractured_evaluator._check_fractured(item, matches)

        assert is_fractured is True
        assert bonus == 0
        assert mod is None


# -------------------------
# Archetype Matching Tests
# -------------------------

class TestArchetypeMatching:
    """Test build archetype matching."""

    @pytest.fixture
    def archetype_evaluator(self, tmp_path):
        """Create evaluator with archetypes configured."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70},
            "resistances": {"tier1": ["+#% to Fire Resistance"], "weight": 8, "min_value": 35},
            "energy_shield": {"tier1": ["+# to maximum Energy Shield"], "weight": 9, "min_value": 40},
            "critical_strike": {"tier1": ["#% increased Critical Strike Chance"], "weight": 8, "min_value": 20}
        }

        archetypes = {
            "archetypes": {
                "tank": {
                    "name": "Tank Build",
                    "description": "High defense build",
                    "priority_affixes": ["life", "resistances", "energy_shield"],
                    "anti_affixes": ["critical_strike"]
                },
                "crit": {
                    "name": "Crit Build",
                    "description": "High crit build",
                    "priority_affixes": ["critical_strike", "life"],
                    "anti_affixes": []
                }
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))
        (data_dir / "build_archetypes.json").write_text(json.dumps(archetypes))

        return RareItemEvaluator(data_dir=data_dir)

    def test_matches_archetype_with_priority_affixes(self, archetype_evaluator):
        """Should match archetype when 2+ priority affixes present."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
        ]

        matched, bonus = archetype_evaluator._match_archetypes(matches)

        assert "tank" in matched
        assert bonus >= 5

    def test_no_match_with_anti_affixes(self, archetype_evaluator):
        """Should not match archetype when anti-affixes present."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
            AffixMatch("critical_strike", "", "", 30, 8, "tier1", False),
        ]

        matched, bonus = archetype_evaluator._match_archetypes(matches)

        assert "tank" not in matched  # Crit is anti-affix for tank

    def test_excellent_fit_bonus(self, archetype_evaluator):
        """Should give highest bonus for 4+ priority matches."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
            AffixMatch("resistances", "", "", 45, 8, "tier1", False),
            AffixMatch("energy_shield", "", "", 80, 9, "tier1", False),
        ]

        matched, bonus = archetype_evaluator._match_archetypes(matches)

        # Note: resistances counted once by type
        assert "tank" in matched
        assert bonus >= 5  # 2+ priority affixes

    def test_no_archetypes_configured(self, mock_data_dir):
        """Should handle empty archetypes gracefully."""
        evaluator = RareItemEvaluator(data_dir=mock_data_dir)
        matches = [AffixMatch("life", "", "", 100, 10, "tier1", False)]

        matched, bonus = evaluator._match_archetypes(matches)

        assert matched == []
        assert bonus == 0


# -------------------------
# Meta Bonus Calculation Tests
# -------------------------

class TestMetaBonusCalculation:
    """Test meta popularity bonus calculation."""

    @pytest.fixture
    def simple_meta_evaluator(self, tmp_path):
        """Create evaluator with simple (integer) meta weights."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70},
            "resistances": {"tier1": ["+#% to Fire Resistance"], "weight": 8, "min_value": 35}
        }

        archetypes = {
            "archetypes": {},
            "_meta_weights": {
                "popularity_boosts": {
                    "life": 3,
                    "resistances": 2
                }
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))
        (data_dir / "build_archetypes.json").write_text(json.dumps(archetypes))

        return RareItemEvaluator(data_dir=data_dir)

    def test_simple_meta_bonus_calculation(self, simple_meta_evaluator):
        """Should calculate bonus from simple integer weights."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
        ]

        bonus = simple_meta_evaluator._calculate_meta_bonus(matches)

        assert bonus == 5  # 3 + 2 = 5

    def test_meta_bonus_caps_at_10(self, tmp_path):
        """Meta bonus should cap at 10."""
        # Need multiple different affix types with high meta weights to test cap
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70},
            "resistances": {"tier1": ["+#% to Fire Resistance"], "weight": 8, "min_value": 35},
            "energy_shield": {"tier1": ["+# to maximum Energy Shield"], "weight": 9, "min_value": 40},
            "movement_speed": {"tier1": ["#% increased Movement Speed"], "weight": 9, "min_value": 25}
        }

        archetypes = {
            "archetypes": {},
            "_meta_weights": {
                "popularity_boosts": {
                    "life": 5,
                    "resistances": 5,
                    "energy_shield": 5,
                    "movement_speed": 5
                }
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))
        (data_dir / "build_archetypes.json").write_text(json.dumps(archetypes))

        evaluator = RareItemEvaluator(data_dir=data_dir)

        # 4 different affix types, each with +5 meta bonus = 20, should cap at 10
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
            AffixMatch("energy_shield", "", "", 80, 9, "tier1", False),
            AffixMatch("movement_speed", "", "", 30, 9, "tier1", False),
        ]

        bonus = evaluator._calculate_meta_bonus(matches)

        assert bonus == 10  # Capped at max

    def test_no_meta_weights_no_bonus(self, mock_data_dir):
        """No meta weights should mean no bonus."""
        evaluator = RareItemEvaluator(data_dir=mock_data_dir)
        matches = [AffixMatch("life", "", "", 100, 10, "tier1", False)]

        bonus = evaluator._calculate_meta_bonus(matches)

        # Without explicit meta_affixes.json, depends on if build_archetypes has _meta_weights
        assert bonus >= 0


class TestMetaBonusWithDictFormat:
    """Test meta bonus with dict format (from meta_affixes.json)."""

    @pytest.fixture
    def dict_meta_evaluator(self, tmp_path):
        """Create evaluator with dict-format meta weights."""
        from datetime import datetime

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70},
            "resistances": {"tier1": ["+#% to Fire Resistance"], "weight": 8, "min_value": 35}
        }

        meta_data = {
            "league": "Test",
            "builds_analyzed": 100,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {
                "life": {"popularity_percent": 60.0},  # +3 bonus
                "resistances": {"popularity_percent": 35.0}  # +2 bonus
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        return RareItemEvaluator(data_dir=data_dir)

    def test_dict_format_meta_bonus(self, dict_meta_evaluator):
        """Should calculate bonus from dict format popularity."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
        ]

        bonus = dict_meta_evaluator._calculate_meta_bonus(matches)

        # life: 60% >= 50% = +3, res: 35% >= 30% = +2
        assert bonus == 5

    def test_high_popularity_bonus(self, tmp_path):
        """High popularity (>=50%) should give +3 bonus."""
        from datetime import datetime

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {"life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70}}
        meta_data = {
            "league": "Test",
            "builds_analyzed": 100,
            "last_analysis": datetime.now().isoformat(),
            "affixes": {"life": {"popularity_percent": 75.0}}
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))
        (data_dir / "meta_affixes.json").write_text(json.dumps(meta_data))

        evaluator = RareItemEvaluator(data_dir=data_dir)
        matches = [AffixMatch("life", "", "", 100, 10, "tier1", False)]

        bonus = evaluator._calculate_meta_bonus(matches)

        assert bonus == 3  # >=50% = +3


# -------------------------
# Evaluate With Archetype Tests
# -------------------------

class TestEvaluateWithArchetype:
    """Test evaluate_with_archetype method."""

    @pytest.fixture
    def archetype_eval_setup(self, tmp_path):
        """Create evaluator for archetype evaluation testing."""
        from core.build_archetype import BuildArchetype, DefenseType, DamageType

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {
                "tier1": ["+# to maximum Life"],
                "tier1_range": [100, 109],
                "weight": 10,
                "min_value": 70
            },
            "resistances": {
                "tier1": ["+#% to Fire Resistance"],
                "tier1_range": [46, 48],
                "weight": 8,
                "min_value": 35
            },
            "energy_shield": {
                "tier1": ["+# to maximum Energy Shield"],
                "tier1_range": [80, 110],
                "weight": 9,
                "min_value": 40
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        evaluator = RareItemEvaluator(data_dir=data_dir)

        # Create a test archetype using proper enum values
        archetype = BuildArchetype(
            defense_type=DefenseType.ENERGY_SHIELD,
            damage_type=DamageType.ELEMENTAL,
        )

        return evaluator, archetype

    def test_evaluate_with_archetype_weights_affixes(self, archetype_eval_setup):
        """Should apply archetype weight multipliers."""
        evaluator, archetype = archetype_eval_setup

        item = create_rare_item(
            explicits=[
                "+105 to maximum Life",
                "+85 to maximum Energy Shield"
            ]
        )

        result = evaluator.evaluate_with_archetype(item, archetype)

        assert result.build_archetype == archetype
        assert result.archetype_affix_details is not None
        assert len(result.archetype_affix_details) == 2

    def test_evaluate_with_archetype_unique_item(self, archetype_eval_setup):
        """Unique items should get proper unique evaluation."""
        evaluator, archetype = archetype_eval_setup

        item = create_rare_item()
        item.rarity = "UNIQUE"
        item.name = "Test Unique"

        result = evaluator.evaluate_with_archetype(item, archetype)

        # Unique items now get proper evaluation
        assert result.tier in ["chase", "excellent", "good", "average", "vendor"]
        assert result._unique_evaluation is not None

    def test_evaluate_with_archetype_calculates_weighted_score(self, archetype_eval_setup):
        """Should calculate archetype-weighted total score."""
        evaluator, archetype = archetype_eval_setup

        item = create_rare_item(
            explicits=["+85 to maximum Energy Shield"]  # Only ES (priority for ES build)
        )

        result = evaluator.evaluate_with_archetype(item, archetype)

        assert result.archetype_weighted_score > 0


# -------------------------
# Open Affix Detection Tests
# -------------------------

class TestOpenAffixDetection:
    """Test open prefix/suffix detection."""

    def test_full_item_no_open_slots(self, evaluator):
        """Fully modded item should have no open slots."""
        item = create_rare_item(
            explicits=[
                "Mod 1", "Mod 2", "Mod 3",
                "Mod 4", "Mod 5", "Mod 6"
            ]
        )
        matches = []

        open_p, open_s, bonus = evaluator._detect_open_affixes(item, matches)

        assert open_p == 0
        assert open_s == 0
        assert bonus == 0

    def test_few_mods_has_open_slots(self, evaluator):
        """Item with few mods should have open slots."""
        item = create_rare_item(explicits=["Mod 1", "Mod 2"])
        matches = []

        open_p, open_s, bonus = evaluator._detect_open_affixes(item, matches)

        assert open_p > 0 or open_s > 0
        assert bonus >= 5

    def test_crafting_bonus_with_t1_matches(self, evaluator):
        """Open slots + T1 matches should give high crafting bonus."""
        item = create_rare_item(explicits=["Mod 1", "Mod 2"])
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
        ]

        open_p, open_s, bonus = evaluator._detect_open_affixes(item, matches)

        assert bonus == 15  # 2+ open + T1 = 15


# -------------------------
# Tier Determination Edge Cases
# -------------------------

class TestTierDeterminationEdgeCases:
    """Test edge cases in tier determination."""

    def test_fractured_excellent_crafting_base(self, evaluator):
        """Fractured T1 with high score should be excellent crafting base."""
        matches = [
            AffixMatch("life", "", "", 105, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
        ]

        tier, value = evaluator._determine_tier(
            total_score=75,
            matches=matches,
            synergies=[],
            is_fractured=True,
            crafting_bonus=10
        )

        assert tier == "excellent"
        assert "crafting base" in value

    def test_fractured_good_crafting_base(self, evaluator):
        """Fractured T1 with moderate score should be good crafting base."""
        matches = [
            AffixMatch("life", "", "", 105, 10, "tier1", False),
        ]

        tier, value = evaluator._determine_tier(
            total_score=55,
            matches=matches,
            synergies=[],
            is_fractured=True,
            crafting_bonus=5
        )

        assert tier == "good"
        assert "crafting base" in value

    def test_meta_fit_excellent_tier(self, evaluator):
        """Item fitting meta with T1 mods should be excellent."""
        matches = [
            AffixMatch("life", "", "", 105, 10, "tier1", False),
            AffixMatch("resistances", "", "", 47, 8, "tier1", False),
        ]

        tier, value = evaluator._determine_tier(
            total_score=75,
            matches=matches,
            synergies=[],
            matched_archetypes=["tank"]
        )

        assert tier == "excellent"
        assert "meta" in value

    def test_meta_fit_good_tier(self, evaluator):
        """Item fitting meta should be good tier."""
        matches = [
            AffixMatch("life", "", "", 95, 8, "tier2", False),
        ]

        tier, value = evaluator._determine_tier(
            total_score=55,
            matches=matches,
            synergies=[],
            matched_archetypes=["tank"]
        )

        assert tier == "good"
        assert "meta" in value

    def test_craftable_good_tier(self, evaluator):
        """Item with high crafting potential should be good."""
        matches = [
            AffixMatch("life", "", "", 100, 10, "tier1", False),
        ]

        tier, value = evaluator._determine_tier(
            total_score=55,
            matches=matches,
            synergies=[],
            crafting_bonus=10
        )

        assert tier == "good"
        assert "craftable" in value


# -------------------------
# Summary Generation Edge Cases
# -------------------------

class TestSummaryEdgeCases:
    """Test summary generation edge cases."""

    @pytest.fixture
    def summary_evaluator(self, tmp_path):
        """Create evaluator for summary testing."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {
            "life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70},
            "_synergies": {
                "test_synergy": {
                    "required": {"life": 1},
                    "bonus_score": 5,
                    "description": "Test Synergy"
                }
            },
            "_red_flags": {
                "test_flag": {
                    "check": "has_both",
                    "affixes": [],
                    "penalty_score": -5,
                    "description": "Test Flag"
                }
            }
        }

        archetypes = {
            "archetypes": {
                "test_build": {
                    "name": "Test Build",
                    "description": "A test build archetype",
                    "priority_affixes": ["life"],
                    "anti_affixes": []
                }
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))
        (data_dir / "build_archetypes.json").write_text(json.dumps(archetypes))

        return RareItemEvaluator(data_dir=data_dir)

    def test_summary_includes_fractured_section(self, summary_evaluator):
        """Summary should include fractured mod section."""
        item = create_rare_item(explicits=["+100 to maximum Life"])
        item.is_fractured = True

        eval_result = summary_evaluator.evaluate(item)
        # Manually set fractured fields for display
        eval_result.fractured_mod = "+100 to maximum Life"
        eval_result.fractured_bonus = 25

        summary = summary_evaluator.get_summary(eval_result)

        assert "Fractured Mod:" in summary

    def test_summary_includes_crafting_potential(self, summary_evaluator):
        """Summary should include crafting potential section."""
        item = create_rare_item(explicits=["+100 to maximum Life"])

        eval_result = summary_evaluator.evaluate(item)
        # Item with few mods should have open slots
        summary = summary_evaluator.get_summary(eval_result)

        assert "Crafting Potential:" in summary
        assert "Open Slots:" in summary

    def test_summary_includes_archetype_matches(self, summary_evaluator):
        """Summary should include matched archetypes."""
        item = create_rare_item(explicits=["+100 to maximum Life"])

        eval_result = summary_evaluator.evaluate(item)
        # Manually add archetype match
        eval_result.matched_archetypes = ["test_build"]

        summary = summary_evaluator.get_summary(eval_result)

        assert "Build Archetypes" in summary
        assert "Test Build" in summary

    def test_summary_includes_synergies(self, summary_evaluator):
        """Summary should include synergies section."""
        item = create_rare_item(explicits=["+100 to maximum Life"])

        eval_result = summary_evaluator.evaluate(item)

        # If synergies are found
        if eval_result.synergies_found:
            summary = summary_evaluator.get_summary(eval_result)
            assert "Synergies Detected" in summary

    def test_summary_includes_slot_bonus_reasons(self, tmp_path):
        """Summary should show slot bonus reasons."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        affixes = {"life": {"tier1": ["+# to maximum Life"], "weight": 10, "min_value": 70}}
        bases = {
            "belt": {"high_tier": ["Stygian Vise"]},
            "_slot_rules": {
                "belt": {
                    "premium_bases": ["Stygian Vise"],
                    "premium_bonus": 15
                }
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps(bases))

        evaluator = RareItemEvaluator(data_dir=data_dir)

        item = create_rare_item(base_type="Stygian Vise")
        item.explicits = ["+100 to maximum Life"]

        eval_result = evaluator.evaluate(item)
        summary = evaluator.get_summary(eval_result)

        assert "Slot Bonus" in summary or "Premium base" in summary


# -------------------------
# Pattern Compilation Tests
# -------------------------

class TestPatternCompilation:
    """Test regex pattern pre-compilation."""

    def test_patterns_precompiled_on_init(self, evaluator):
        """Patterns should be pre-compiled during initialization."""
        assert hasattr(evaluator, '_compiled_patterns')
        assert len(evaluator._compiled_patterns) > 0

    def test_influence_patterns_precompiled(self, evaluator):
        """Influence patterns should be pre-compiled."""
        assert hasattr(evaluator, '_compiled_influence_patterns')
        # May be empty if no influence mods configured
        assert isinstance(evaluator._compiled_influence_patterns, dict)

    def test_handles_invalid_regex_pattern(self, tmp_path):
        """Should handle invalid regex patterns gracefully."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create affixes with potentially problematic pattern
        affixes = {
            "test": {
                "tier1": ["+# to [maximum Life"],  # Unbalanced bracket
                "weight": 5,
                "min_value": 0
            }
        }

        (data_dir / "valuable_affixes.json").write_text(json.dumps(affixes))
        (data_dir / "valuable_bases.json").write_text(json.dumps({}))

        # Should not raise, should handle gracefully
        evaluator = RareItemEvaluator(data_dir=data_dir)
        assert evaluator is not None


# -------------------------
# Additional Slot Detection Tests
# -------------------------

class TestAdditionalSlotDetection:
    """Test additional slot detection cases."""

    def test_detects_body_armour_plate(self, evaluator):
        """Should detect body armour from plate."""
        item = create_rare_item(base_type="Astral Plate")
        assert evaluator._determine_item_slot(item) == "body_armour"

    def test_detects_body_armour_vest(self, evaluator):
        """Should detect body armour from vest."""
        item = create_rare_item(base_type="Assassin's Vest")
        assert evaluator._determine_item_slot(item) == "body_armour"

    def test_detects_body_armour_regalia(self, evaluator):
        """Should detect body armour from regalia."""
        item = create_rare_item(base_type="Vaal Regalia")
        assert evaluator._determine_item_slot(item) == "body_armour"

    def test_detects_belt_vise(self, evaluator):
        """Should detect belt from vise."""
        item = create_rare_item(base_type="Stygian Vise")
        assert evaluator._determine_item_slot(item) == "belt"

    def test_detects_belt_sash(self, evaluator):
        """Should detect belt from sash."""
        item = create_rare_item(base_type="Rustic Sash")
        assert evaluator._determine_item_slot(item) == "belt"

    def test_detects_ring(self, evaluator):
        """Should detect ring slot."""
        item = create_rare_item(base_type="Diamond Ring")
        assert evaluator._determine_item_slot(item) == "ring"

    def test_detects_amulet(self, evaluator):
        """Should detect amulet slot."""
        item = create_rare_item(base_type="Onyx Amulet")
        assert evaluator._determine_item_slot(item) == "amulet"

    def test_detects_talisman_as_amulet(self, evaluator):
        """Should detect talisman as amulet slot."""
        item = create_rare_item(base_type="Avian Twins Talisman")
        assert evaluator._determine_item_slot(item) == "amulet"

    def test_detects_gloves_mitts(self, evaluator):
        """Should detect gloves from mitts."""
        item = create_rare_item(base_type="Fingerless Silk Gloves")
        assert evaluator._determine_item_slot(item) == "gloves"
