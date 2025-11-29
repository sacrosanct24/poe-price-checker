"""Tests for core/build_priorities.py - Build stat priorities."""
import pytest

from core.build_priorities import (
    PriorityTier,
    AVAILABLE_STATS,
    StatPriority,
    BuildPriorities,
    suggest_priorities_from_build,
)


class TestPriorityTier:
    """Tests for PriorityTier enum."""

    def test_tier_values(self):
        """Tiers should have expected values."""
        assert PriorityTier.CRITICAL.value == "critical"
        assert PriorityTier.IMPORTANT.value == "important"
        assert PriorityTier.NICE_TO_HAVE.value == "nice_to_have"


class TestAvailableStats:
    """Tests for AVAILABLE_STATS constant."""

    def test_has_defensive_stats(self):
        """Should have defensive stats."""
        assert "life" in AVAILABLE_STATS
        assert "energy_shield" in AVAILABLE_STATS
        assert "armour" in AVAILABLE_STATS
        assert "evasion" in AVAILABLE_STATS

    def test_has_resistance_stats(self):
        """Should have resistance stats."""
        assert "fire_resistance" in AVAILABLE_STATS
        assert "cold_resistance" in AVAILABLE_STATS
        assert "lightning_resistance" in AVAILABLE_STATS
        assert "chaos_resistance" in AVAILABLE_STATS

    def test_has_attribute_stats(self):
        """Should have attribute stats."""
        assert "strength" in AVAILABLE_STATS
        assert "dexterity" in AVAILABLE_STATS
        assert "intelligence" in AVAILABLE_STATS

    def test_has_offensive_stats(self):
        """Should have offensive stats."""
        assert "attack_speed" in AVAILABLE_STATS
        assert "critical_strike_chance" in AVAILABLE_STATS
        assert "spell_damage" in AVAILABLE_STATS

    def test_stat_display_names(self):
        """Stats should have human-readable display names."""
        assert AVAILABLE_STATS["life"] == "Maximum Life"
        assert AVAILABLE_STATS["fire_resistance"] == "Fire Resistance"


class TestStatPriority:
    """Tests for StatPriority dataclass."""

    def test_create_basic(self):
        """Should create basic priority."""
        priority = StatPriority(
            stat_type="life",
            tier=PriorityTier.CRITICAL,
        )

        assert priority.stat_type == "life"
        assert priority.tier == PriorityTier.CRITICAL
        assert priority.min_value is None
        assert priority.notes == ""

    def test_create_with_options(self):
        """Should create priority with all options."""
        priority = StatPriority(
            stat_type="fire_resistance",
            tier=PriorityTier.IMPORTANT,
            min_value=75,
            notes="Need to cap resists",
        )

        assert priority.min_value == 75
        assert priority.notes == "Need to cap resists"

    def test_to_dict(self):
        """Should serialize to dictionary."""
        priority = StatPriority(
            stat_type="life",
            tier=PriorityTier.CRITICAL,
            min_value=100,
            notes="Test note",
        )

        data = priority.to_dict()

        assert data["stat_type"] == "life"
        assert data["tier"] == "critical"
        assert data["min_value"] == 100
        assert data["notes"] == "Test note"

    def test_from_dict(self):
        """Should deserialize from dictionary."""
        data = {
            "stat_type": "energy_shield",
            "tier": "important",
            "min_value": 500,
            "notes": "ES build",
        }

        priority = StatPriority.from_dict(data)

        assert priority.stat_type == "energy_shield"
        assert priority.tier == PriorityTier.IMPORTANT
        assert priority.min_value == 500
        assert priority.notes == "ES build"

    def test_from_dict_minimal(self):
        """Should deserialize minimal dictionary."""
        data = {
            "stat_type": "life",
            "tier": "critical",
        }

        priority = StatPriority.from_dict(data)

        assert priority.stat_type == "life"
        assert priority.tier == PriorityTier.CRITICAL
        assert priority.min_value is None
        assert priority.notes == ""


class TestBuildPriorities:
    """Tests for BuildPriorities dataclass."""

    def test_create_default(self):
        """Should create with default values."""
        priorities = BuildPriorities()

        assert priorities.critical == []
        assert priorities.important == []
        assert priorities.nice_to_have == []
        assert priorities.is_life_build is True
        assert priorities.is_es_build is False

    def test_add_priority_critical(self):
        """Should add priority to critical tier."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)

        assert len(priorities.critical) == 1
        assert priorities.critical[0].stat_type == "life"
        assert len(priorities.important) == 0
        assert len(priorities.nice_to_have) == 0

    def test_add_priority_important(self):
        """Should add priority to important tier."""
        priorities = BuildPriorities()
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT, min_value=75)

        assert len(priorities.important) == 1
        assert priorities.important[0].stat_type == "fire_resistance"
        assert priorities.important[0].min_value == 75

    def test_add_priority_nice_to_have(self):
        """Should add priority to nice_to_have tier."""
        priorities = BuildPriorities()
        priorities.add_priority("movement_speed", PriorityTier.NICE_TO_HAVE)

        assert len(priorities.nice_to_have) == 1
        assert priorities.nice_to_have[0].stat_type == "movement_speed"

    def test_add_priority_removes_from_other_tiers(self):
        """Adding priority should remove from other tiers first."""
        priorities = BuildPriorities()

        # Add to critical
        priorities.add_priority("life", PriorityTier.CRITICAL)
        assert len(priorities.critical) == 1

        # Move to important - should remove from critical
        priorities.add_priority("life", PriorityTier.IMPORTANT)
        assert len(priorities.critical) == 0
        assert len(priorities.important) == 1

    def test_remove_priority(self):
        """Should remove priority from all tiers."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)

        priorities.remove_priority("life")

        assert len(priorities.critical) == 0
        assert len(priorities.important) == 1

    def test_remove_priority_nonexistent(self):
        """Removing nonexistent priority should not error."""
        priorities = BuildPriorities()
        priorities.remove_priority("nonexistent")  # Should not raise

    def test_get_priority_found(self):
        """Should return priority if set."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL, min_value=100)

        result = priorities.get_priority("life")

        assert result is not None
        assert result.stat_type == "life"
        assert result.min_value == 100

    def test_get_priority_not_found(self):
        """Should return None if not set."""
        priorities = BuildPriorities()
        assert priorities.get_priority("life") is None

    def test_get_priority_searches_all_tiers(self):
        """Should search all tiers."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)
        priorities.add_priority("movement_speed", PriorityTier.NICE_TO_HAVE)

        assert priorities.get_priority("life") is not None
        assert priorities.get_priority("fire_resistance") is not None
        assert priorities.get_priority("movement_speed") is not None

    def test_get_all_priorities_order(self):
        """Should return all priorities in tier order."""
        priorities = BuildPriorities()
        priorities.add_priority("movement_speed", PriorityTier.NICE_TO_HAVE)
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT)

        all_priorities = priorities.get_all_priorities()

        assert len(all_priorities) == 3
        # Critical should be first
        assert all_priorities[0].stat_type == "life"
        # Important second
        assert all_priorities[1].stat_type == "fire_resistance"
        # Nice to have last
        assert all_priorities[2].stat_type == "movement_speed"

    def test_to_dict(self):
        """Should serialize to dictionary."""
        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL)
        priorities.is_es_build = True

        data = priorities.to_dict()

        assert len(data["critical"]) == 1
        assert data["critical"][0]["stat_type"] == "life"
        assert data["is_es_build"] is True

    def test_from_dict(self):
        """Should deserialize from dictionary."""
        data = {
            "critical": [{"stat_type": "life", "tier": "critical"}],
            "important": [{"stat_type": "fire_resistance", "tier": "important"}],
            "nice_to_have": [],
            "is_life_build": True,
            "is_es_build": False,
            "is_hybrid": False,
            "uses_attack": True,
            "uses_spell": False,
            "uses_dot": False,
            "uses_minions": False,
        }

        priorities = BuildPriorities.from_dict(data)

        assert len(priorities.critical) == 1
        assert len(priorities.important) == 1
        assert priorities.uses_attack is True

    def test_serialization_roundtrip(self):
        """Serialize then deserialize should preserve data."""
        original = BuildPriorities()
        original.add_priority("life", PriorityTier.CRITICAL, min_value=100, notes="Test")
        original.add_priority("fire_resistance", PriorityTier.IMPORTANT)
        original.is_es_build = True
        original.uses_minions = True

        data = original.to_dict()
        restored = BuildPriorities.from_dict(data)

        assert len(restored.critical) == len(original.critical)
        assert restored.critical[0].min_value == 100
        assert restored.critical[0].notes == "Test"
        assert restored.is_es_build is True
        assert restored.uses_minions is True


class TestSuggestPrioritiesFromBuild:
    """Tests for suggest_priorities_from_build function."""

    def test_detects_life_build(self):
        """Should detect life-based build."""
        stats = {
            "Life": 5000.0,
            "EnergyShield": 100.0,
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.is_life_build is True
        assert priorities.is_es_build is False
        assert priorities.get_priority("life") is not None
        assert priorities.get_priority("life").tier == PriorityTier.CRITICAL

    def test_detects_es_build(self):
        """Should detect ES-based build."""
        stats = {
            "Life": 1000.0,
            "EnergyShield": 8000.0,
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.is_life_build is False
        assert priorities.is_es_build is True
        assert priorities.get_priority("energy_shield") is not None

    def test_detects_hybrid_build(self):
        """Should detect hybrid build."""
        stats = {
            "Life": 3000.0,
            "EnergyShield": 3000.0,
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.is_hybrid is True

    def test_suggests_resistance_needs(self):
        """Should suggest resistances when overcap is low."""
        stats = {
            "Life": 5000.0,
            "EnergyShield": 100.0,
            "FireResistOverCap": 10.0,  # Low
            "ColdResistOverCap": 50.0,   # OK
            "LightningResistOverCap": 5.0,  # Low
            "ChaosResist": 20.0,  # Low
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.get_priority("fire_resistance") is not None
        assert priorities.get_priority("lightning_resistance") is not None
        assert priorities.get_priority("chaos_resistance") is not None
        # Cold should NOT be prioritized (overcap is good)
        assert priorities.get_priority("cold_resistance") is None

    def test_suggests_attribute_needs(self):
        """Should suggest attributes when close to requirements."""
        stats = {
            "Life": 5000.0,
            "EnergyShield": 100.0,
            "Str": 110.0,
            "ReqStr": 100.0,  # Only 10 over - too close
            "Dex": 150.0,
            "ReqDex": 100.0,  # 50 over - OK
            "Int": 130.0,
            "ReqInt": 120.0,  # Only 10 over - too close
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.get_priority("strength") is not None
        assert priorities.get_priority("intelligence") is not None
        # Dex should NOT be prioritized (comfortable margin)
        assert priorities.get_priority("dexterity") is None

    def test_detects_dot_build(self):
        """Should detect DoT-focused build."""
        stats = {
            "Life": 5000.0,
            "EnergyShield": 100.0,
            "CombinedDPS": 100000.0,
            "TotalDotDPS": 200000.0,  # More than 50% of combined
        }

        priorities = suggest_priorities_from_build(stats)

        assert priorities.uses_dot is True
        assert priorities.get_priority("damage_over_time") is not None

    def test_always_suggests_movement_speed(self):
        """Should always suggest movement speed as nice to have."""
        stats = {
            "Life": 5000.0,
            "EnergyShield": 100.0,
        }

        priorities = suggest_priorities_from_build(stats)

        ms = priorities.get_priority("movement_speed")
        assert ms is not None
        assert ms.tier == PriorityTier.NICE_TO_HAVE

    def test_handles_missing_stats(self):
        """Should handle missing stats gracefully."""
        stats = {}  # Empty stats

        priorities = suggest_priorities_from_build(stats)

        # Should not crash, should return valid object
        assert priorities is not None
        assert isinstance(priorities, BuildPriorities)
