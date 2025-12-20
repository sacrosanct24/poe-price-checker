"""
Tests for the Build Archetype detection system.

Tests:
- DefenseType, DamageType, AttackType enums
- BuildArchetype dataclass
- Archetype detection from PoB stats
- Weight multiplier calculations
"""
import pytest
from core.build_archetype import (
    # Enums
    DefenseType, DamageType, AttackType,
    # Dataclass
    BuildArchetype,
    # Detection functions
    detect_archetype, get_default_archetype,
    # Weight functions
    load_archetype_weights, get_weight_multiplier, apply_archetype_weights,
)


class TestEnums:
    """Tests for archetype enums."""

    def test_defense_types(self):
        """Test DefenseType enum values."""
        assert DefenseType.LIFE.value == "life"
        assert DefenseType.ENERGY_SHIELD.value == "es"
        assert DefenseType.HYBRID.value == "hybrid"
        assert DefenseType.LOW_LIFE.value == "low_life"

    def test_damage_types(self):
        """Test DamageType enum values."""
        assert DamageType.PHYSICAL.value == "physical"
        assert DamageType.FIRE.value == "fire"
        assert DamageType.COLD.value == "cold"
        assert DamageType.LIGHTNING.value == "lightning"
        assert DamageType.CHAOS.value == "chaos"
        assert DamageType.MINION.value == "minion"

    def test_attack_types(self):
        """Test AttackType enum values."""
        assert AttackType.ATTACK.value == "attack"
        assert AttackType.SPELL.value == "spell"
        assert AttackType.MINION.value == "minion"
        assert AttackType.DOT.value == "dot"


class TestBuildArchetype:
    """Tests for BuildArchetype dataclass."""

    def test_default_archetype(self):
        """Test default archetype values."""
        arch = BuildArchetype()
        assert arch.defense_type == DefenseType.LIFE
        assert arch.damage_type == DamageType.PHYSICAL
        assert arch.attack_type == AttackType.ATTACK
        assert arch.is_crit is False
        assert arch.confidence == 0.5

    def test_archetype_to_dict(self):
        """Test serialization to dict."""
        arch = BuildArchetype(
            defense_type=DefenseType.ENERGY_SHIELD,
            damage_type=DamageType.COLD,
            is_crit=True,
            primary_element="cold",
        )
        data = arch.to_dict()

        assert data["defense_type"] == "es"
        assert data["damage_type"] == "cold"
        assert data["is_crit"] is True
        assert data["primary_element"] == "cold"

    def test_archetype_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "defense_type": "es",
            "damage_type": "fire",
            "attack_type": "spell",
            "is_crit": True,
            "primary_element": "fire",
            "confidence": 0.9,
        }
        arch = BuildArchetype.from_dict(data)

        assert arch.defense_type == DefenseType.ENERGY_SHIELD
        assert arch.damage_type == DamageType.FIRE
        assert arch.attack_type == AttackType.SPELL
        assert arch.is_crit is True
        assert arch.primary_element == "fire"
        assert arch.confidence == 0.9

    def test_get_summary_life_crit_attack(self):
        """Test summary for life-based crit attack."""
        arch = BuildArchetype(
            defense_type=DefenseType.LIFE,
            damage_type=DamageType.PHYSICAL,
            attack_type=AttackType.ATTACK,
            is_crit=True,
        )
        summary = arch.get_summary()
        assert "Life-based" in summary
        assert "Physical" in summary
        assert "Attack" in summary
        assert "Crit" in summary

    def test_get_summary_es_spell(self):
        """Test summary for ES spell caster."""
        arch = BuildArchetype(
            defense_type=DefenseType.ENERGY_SHIELD,
            damage_type=DamageType.COLD,
            attack_type=AttackType.SPELL,
            primary_element="cold",
        )
        summary = arch.get_summary()
        assert "ES-based" in summary
        assert "Cold" in summary
        assert "Spell" in summary

    def test_get_summary_minion(self):
        """Test summary for minion build."""
        arch = BuildArchetype(
            is_minion=True,
            damage_type=DamageType.MINION,
            attack_type=AttackType.MINION,
        )
        summary = arch.get_summary()
        assert "Minion" in summary


class TestArchetypeDetection:
    """Tests for archetype detection from stats."""

    def test_detect_life_build(self):
        """Test detection of life-based build."""
        stats = {
            "Life": 5500,
            "EnergyShield": 200,
        }
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.LIFE
        assert arch.confidence > 0.5

    def test_detect_es_build(self):
        """Test detection of ES-based build."""
        stats = {
            "Life": 1200,
            "EnergyShield": 8500,
        }
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.ENERGY_SHIELD

    def test_detect_hybrid_build(self):
        """Test detection of hybrid build."""
        stats = {
            "Life": 3500,
            "EnergyShield": 3000,
        }
        arch = detect_archetype(stats)
        assert arch.defense_type == DefenseType.HYBRID

    def test_detect_crit_build(self):
        """Test detection of crit-based build."""
        stats = {
            "Life": 5000,
            "CritChance": 65,
            "CritMultiplier": 450,
        }
        arch = detect_archetype(stats)
        assert arch.is_crit is True

    def test_detect_non_crit_build(self):
        """Test non-crit build is detected correctly."""
        stats = {
            "Life": 5000,
            "CritChance": 5,
        }
        arch = detect_archetype(stats)
        assert arch.is_crit is False

    def test_detect_physical_damage(self):
        """Test detection of physical damage build."""
        stats = {
            "PhysicalDPS": 1500000,
            "FireDPS": 100000,
        }
        arch = detect_archetype(stats)
        assert arch.damage_type == DamageType.PHYSICAL

    def test_detect_elemental_fire(self):
        """Test detection of fire elemental build."""
        stats = {
            "FireDPS": 2000000,
            "ColdDPS": 100000,
            "PhysicalDPS": 50000,
        }
        arch = detect_archetype(stats)
        assert arch.damage_type == DamageType.FIRE
        assert arch.primary_element == "fire"

    def test_detect_minion_build(self):
        """Test detection of minion build."""
        stats = {
            "MinionDPS": 5000000,
            "PhysicalDPS": 10000,
        }
        arch = detect_archetype(stats)
        assert arch.is_minion is True
        assert arch.damage_type == DamageType.MINION

    def test_detect_spell_from_skill_name(self):
        """Test spell detection from skill name."""
        stats = {"Life": 5000}
        arch = detect_archetype(stats, "Ice Spear")
        assert arch.attack_type == AttackType.SPELL

    def test_detect_attack_from_skill_name(self):
        """Test attack detection from skill name."""
        stats = {"Life": 5000}
        arch = detect_archetype(stats, "Cyclone")
        assert arch.attack_type == AttackType.ATTACK

    def test_detect_resistance_needs(self):
        """Test resistance needs detection."""
        stats = {
            "Life": 5000,
            "FireResistOverCap": 5,  # Low
            "ColdResistOverCap": 50,
            "LightningResistOverCap": 30,
            "ChaosResist": -30,  # Negative
        }
        arch = detect_archetype(stats)
        assert arch.needs_fire_res is True
        assert arch.needs_cold_res is False
        assert arch.needs_lightning_res is False
        assert arch.needs_chaos_res is True

    def test_detect_attribute_needs(self):
        """Test attribute needs detection."""
        stats = {
            "Life": 5000,
            "Strength": 200,  # High
            "Dexterity": 80,  # Low
            "Intelligence": 180,  # High
        }
        arch = detect_archetype(stats)
        assert arch.needs_strength is True
        assert arch.needs_dexterity is False
        assert arch.needs_intelligence is True


class TestDefaultArchetype:
    """Tests for default archetype."""

    def test_get_default_archetype(self):
        """Test getting default archetype."""
        arch = get_default_archetype()
        assert arch.defense_type == DefenseType.LIFE
        assert arch.damage_type == DamageType.PHYSICAL
        assert arch.attack_type == AttackType.ATTACK
        assert arch.confidence == 0.0


class TestWeightLoading:
    """Tests for weight file loading."""

    def test_load_weights(self):
        """Test loading weights from JSON."""
        weights = load_archetype_weights()
        assert weights is not None
        assert "defense_types" in weights
        assert "damage_types" in weights
        assert "flags" in weights

    def test_weight_structure(self):
        """Test weight structure."""
        weights = load_archetype_weights()

        # Check defense types
        assert "life" in weights["defense_types"]
        assert "es" in weights["defense_types"]

        # Check damage types
        assert "physical" in weights["damage_types"]
        assert "fire" in weights["damage_types"]

        # Check flags
        assert "is_crit" in weights["flags"]


class TestWeightMultipliers:
    """Tests for weight multiplier calculations."""

    def test_life_build_life_weight(self):
        """Test life weight for life build."""
        arch = BuildArchetype(defense_type=DefenseType.LIFE)
        mult = get_weight_multiplier(arch, "life")
        assert mult > 1.0  # Life should be boosted for life builds

    def test_life_build_es_weight(self):
        """Test ES weight for life build."""
        arch = BuildArchetype(defense_type=DefenseType.LIFE)
        mult = get_weight_multiplier(arch, "energy_shield")
        assert mult < 1.0  # ES should be reduced for life builds

    def test_es_build_es_weight(self):
        """Test ES weight for ES build."""
        arch = BuildArchetype(defense_type=DefenseType.ENERGY_SHIELD)
        mult = get_weight_multiplier(arch, "energy_shield")
        assert mult > 1.0  # ES should be boosted for ES builds

    def test_crit_build_crit_weight(self):
        """Test crit weight for crit build."""
        arch = BuildArchetype(is_crit=True)
        mult = get_weight_multiplier(arch, "critical_strike_chance")
        assert mult > 1.0  # Crit should be boosted for crit builds

    def test_fire_build_fire_weight(self):
        """Test fire damage weight for fire build."""
        arch = BuildArchetype(damage_type=DamageType.FIRE)
        mult = get_weight_multiplier(arch, "fire_damage")
        assert mult > 1.0  # Fire damage should be boosted

    def test_resistance_needs_weight(self):
        """Test resistance weight when needed."""
        arch = BuildArchetype(needs_fire_res=True)
        mult = get_weight_multiplier(arch, "fire_resistance")
        assert mult > 1.0  # Fire res should be boosted when needed

    def test_unknown_affix_weight(self):
        """Test unknown affix returns 1.0."""
        arch = BuildArchetype()
        mult = get_weight_multiplier(arch, "unknown_affix_xyz")
        assert mult == 1.0


class TestApplyArchetypeWeights:
    """Tests for applying archetype weights to scores."""

    def test_apply_weights(self):
        """Test applying weights to affix scores."""
        arch = BuildArchetype(defense_type=DefenseType.LIFE)
        scores = {
            "life": 100.0,
            "energy_shield": 100.0,
            "fire_resistance": 50.0,
        }
        weighted = apply_archetype_weights(arch, scores)

        # Life should be boosted
        assert weighted["life"] > scores["life"]
        # ES should be reduced
        assert weighted["energy_shield"] < scores["energy_shield"]

    def test_apply_weights_preserves_unmatched(self):
        """Test that unmatched affixes keep original scores."""
        arch = BuildArchetype()
        scores = {"unknown_stat": 100.0}
        weighted = apply_archetype_weights(arch, scores)
        assert weighted["unknown_stat"] == 100.0


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test full detection and weighting workflow."""
        # Simulate a life-based crit fire attack build
        stats = {
            "Life": 5500,
            "EnergyShield": 200,
            "CritChance": 60,
            "CritMultiplier": 400,
            "FireDPS": 2000000,
            "PhysicalDPS": 500000,
            "FireResistOverCap": 5,
        }

        # Detect archetype
        arch = detect_archetype(stats)

        assert arch.defense_type == DefenseType.LIFE
        assert arch.is_crit is True
        assert arch.needs_fire_res is True

        # Apply weights
        base_scores = {
            "life": 100.0,
            "critical_strike_chance": 50.0,
            "fire_resistance": 30.0,
            "energy_shield": 80.0,
        }

        weighted = apply_archetype_weights(arch, base_scores)

        # Life should be high (life build)
        assert weighted["life"] > base_scores["life"]

        # Crit should be high (crit build)
        assert weighted["critical_strike_chance"] > base_scores["critical_strike_chance"]

        # Fire res should be high (needs it)
        assert weighted["fire_resistance"] > base_scores["fire_resistance"]

        # ES should be low (life build)
        assert weighted["energy_shield"] < base_scores["energy_shield"]

    def test_archetype_serialization_roundtrip(self):
        """Test archetype survives serialization roundtrip."""
        arch = BuildArchetype(
            defense_type=DefenseType.ENERGY_SHIELD,
            damage_type=DamageType.COLD,
            attack_type=AttackType.SPELL,
            is_crit=True,
            primary_element="cold",
            needs_chaos_res=True,
            confidence=0.85,
        )

        # Serialize and deserialize
        data = arch.to_dict()
        restored = BuildArchetype.from_dict(data)

        assert restored.defense_type == arch.defense_type
        assert restored.damage_type == arch.damage_type
        assert restored.attack_type == arch.attack_type
        assert restored.is_crit == arch.is_crit
        assert restored.primary_element == arch.primary_element
        assert restored.needs_chaos_res == arch.needs_chaos_res
        assert restored.confidence == arch.confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
