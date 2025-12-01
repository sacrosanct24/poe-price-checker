"""
Tests for Smart Trade Filters.

Tests:
- Filter priority ordering
- Gap-based filter generation
- Archetype-based filter selection
- Slot-specific filters
"""
import pytest
from core.smart_trade_filters import (
    SmartFilterBuilder,
    SmartFilterResult,
    FilterPriority,
    build_smart_filters,
)
from core.build_archetype import (
    BuildArchetype,
    DefenseType,
    AttackType,
    detect_archetype,
)
from core.build_stat_calculator import BuildStats


class TestFilterPriority:
    """Tests for FilterPriority dataclass."""

    def test_create_filter(self):
        """Test creating a filter priority."""
        f = FilterPriority(
            stat_id="pseudo.pseudo_total_life",
            min_value=60,
            priority=10,
            reason="Life build",
        )
        assert f.stat_id == "pseudo.pseudo_total_life"
        assert f.min_value == 60
        assert f.priority == 10


class TestSmartFilterResult:
    """Tests for SmartFilterResult."""

    def test_to_trade_filters_basic(self):
        """Test converting to trade API format."""
        result = SmartFilterResult(
            filters=[
                FilterPriority("stat1", min_value=50, priority=10),
                FilterPriority("stat2", min_value=30, priority=20),
            ]
        )
        trade_filters = result.to_trade_filters()

        assert len(trade_filters) == 2
        assert trade_filters[0]["id"] == "stat1"
        assert trade_filters[0]["value"]["min"] == 50

    def test_to_trade_filters_respects_max(self):
        """Test that max_filters is respected."""
        result = SmartFilterResult(
            filters=[
                FilterPriority(f"stat{i}", min_value=i, priority=i)
                for i in range(10)
            ]
        )
        trade_filters = result.to_trade_filters(max_filters=3)

        assert len(trade_filters) == 3

    def test_to_trade_filters_sorted_by_priority(self):
        """Test that filters are sorted by priority."""
        result = SmartFilterResult(
            filters=[
                FilterPriority("low", min_value=10, priority=30),
                FilterPriority("high", min_value=20, priority=0),
                FilterPriority("med", min_value=15, priority=15),
            ]
        )
        trade_filters = result.to_trade_filters()

        # Should be sorted: high (0), med (15), low (30)
        assert trade_filters[0]["id"] == "high"
        assert trade_filters[1]["id"] == "med"
        assert trade_filters[2]["id"] == "low"


class TestSmartFilterBuilderGaps:
    """Tests for gap-based filter generation."""

    def test_fire_resistance_gap(self):
        """Test filter for fire resistance gap."""
        stats = BuildStats(fire_overcap=-15.0)  # 15% under cap
        builder = SmartFilterBuilder(build_stats=stats)
        result = builder.build_filters()

        fire_filters = [f for f in result.filters if "fire" in f.stat_id]
        assert len(fire_filters) >= 1
        assert fire_filters[0].is_critical is True

    def test_cold_resistance_gap(self):
        """Test filter for cold resistance gap."""
        stats = BuildStats(cold_overcap=-20.0)  # 20% under cap
        builder = SmartFilterBuilder(build_stats=stats)
        result = builder.build_filters()

        cold_filters = [f for f in result.filters if "cold" in f.stat_id]
        assert len(cold_filters) >= 1

    def test_chaos_resistance_gap(self):
        """Test filter for chaos resistance gap."""
        stats = BuildStats(chaos_res=10.0)  # 65% gap to cap
        builder = SmartFilterBuilder(build_stats=stats)
        result = builder.build_filters()

        chaos_filters = [f for f in result.filters if "chaos" in f.stat_id]
        assert len(chaos_filters) >= 1
        assert chaos_filters[0].is_critical is False  # Chaos is not critical

    def test_no_gap_when_overcapped(self):
        """Test no gap filters when resistances are capped."""
        stats = BuildStats(
            fire_overcap=20.0,
            cold_overcap=15.0,
            lightning_overcap=10.0,
            chaos_res=75.0,
        )
        builder = SmartFilterBuilder(build_stats=stats)
        result = builder.build_filters()

        # Should not have resistance gap filters
        gap_filters = [f for f in result.filters if f.is_critical]
        assert len(gap_filters) == 0


class TestSmartFilterBuilderArchetype:
    """Tests for archetype-based filter generation."""

    def test_life_build_filters(self):
        """Test filters for life-based build."""
        archetype = BuildArchetype(defense_type=DefenseType.LIFE)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters()

        life_filters = [f for f in result.filters if "life" in f.stat_id]
        assert len(life_filters) >= 1

    def test_es_build_filters(self):
        """Test filters for ES-based build."""
        archetype = BuildArchetype(defense_type=DefenseType.ENERGY_SHIELD)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters()

        es_filters = [f for f in result.filters if "energy_shield" in f.stat_id]
        assert len(es_filters) >= 1

    def test_hybrid_build_filters(self):
        """Test filters for hybrid build."""
        archetype = BuildArchetype(defense_type=DefenseType.HYBRID)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters()

        life_filters = [f for f in result.filters if "life" in f.stat_id]
        es_filters = [f for f in result.filters if "energy_shield" in f.stat_id]

        assert len(life_filters) >= 1
        assert len(es_filters) >= 1

    def test_crit_build_filters(self):
        """Test filters for crit build."""
        archetype = BuildArchetype(is_crit=True)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters()

        crit_filters = [f for f in result.filters if "crit" in f.stat_id.lower()]
        assert len(crit_filters) >= 1

    def test_attack_build_filters(self):
        """Test filters for attack build."""
        archetype = BuildArchetype(attack_type=AttackType.ATTACK)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters()

        as_filters = [f for f in result.filters if "attack_speed" in f.stat_id]
        assert len(as_filters) >= 1

    def test_spell_build_filters(self):
        """Test filters for spell build."""
        archetype = BuildArchetype(attack_type=AttackType.SPELL)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters()

        cs_filters = [f for f in result.filters if "cast_speed" in f.stat_id]
        assert len(cs_filters) >= 1

    def test_needs_strength_filters(self):
        """Test filters when build needs strength."""
        archetype = BuildArchetype(needs_strength=True)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters()

        str_filters = [f for f in result.filters if "strength" in f.stat_id]
        assert len(str_filters) >= 1


class TestSmartFilterBuilderSlots:
    """Tests for slot-specific filter generation."""

    def test_boots_movement_speed(self):
        """Test boots get movement speed filter."""
        builder = SmartFilterBuilder()
        result = builder.build_filters(slot="Boots")

        ms_reasons = [r for r in result.filter_reasons if "movement" in r.lower()]
        assert len(ms_reasons) >= 1

    def test_gloves_attack_speed(self):
        """Test gloves get attack speed for attack builds."""
        archetype = BuildArchetype(attack_type=AttackType.ATTACK)
        builder = SmartFilterBuilder(archetype=archetype)
        result = builder.build_filters(slot="Gloves")

        as_filters = [f for f in result.filters if "attack_speed" in f.stat_id]
        # Should have at least attack speed (from archetype) and possibly from slot
        assert len(as_filters) >= 1


class TestBuildSmartFiltersFunction:
    """Tests for the convenience function."""

    def test_returns_tuple(self):
        """Test that function returns tuple."""
        filters, result = build_smart_filters()

        assert isinstance(filters, list)
        assert isinstance(result, SmartFilterResult)

    def test_respects_max_filters(self):
        """Test that max_filters is respected."""
        archetype = BuildArchetype(
            defense_type=DefenseType.LIFE,
            is_crit=True,
            attack_type=AttackType.ATTACK,
            needs_strength=True,
        )
        stats = BuildStats(
            fire_overcap=-20.0,
            cold_overcap=-15.0,
            chaos_res=10.0,
        )

        filters, _ = build_smart_filters(
            archetype=archetype,
            build_stats=stats,
            max_filters=4,
        )

        assert len(filters) <= 4


class TestIntegration:
    """Integration tests."""

    def test_full_workflow(self):
        """Test full smart filter generation workflow."""
        # Simulate detecting archetype from PoB stats
        pob_stats = {
            "Life": 5500,
            "EnergyShield": 200,
            "CritChance": 65,
            "CritMultiplier": 450,
            "FireResistOverCap": -5,
            "ColdResistOverCap": 20,
            "LightningResistOverCap": 15,
            "ChaosResist": 30,
            "Str": 180,
        }

        build_stats = BuildStats.from_pob_stats(pob_stats)
        archetype = detect_archetype(pob_stats, "Cyclone")

        filters, result = build_smart_filters(
            archetype=archetype,
            build_stats=build_stats,
            slot="Boots",
            max_filters=6,
        )

        # Should have archetype summary
        assert result.archetype_summary != ""

        # Should have multiple filters
        assert len(filters) >= 3

        # Should include movement speed for boots
        ms_filters = [f for f in filters if "2250533757" in f["id"]]
        assert len(ms_filters) >= 1

        # Filters should have proper structure
        for f in filters:
            assert "id" in f
            # Most filters should have value
            if f["id"].startswith("pseudo") or f["id"].startswith("explicit"):
                assert "value" in f

    def test_default_filters_without_context(self):
        """Test that default filters work without build context."""
        filters, result = build_smart_filters()

        # Should have at least some default filters
        assert len(filters) >= 1

        # Should have reason for using defaults
        assert any("default" in r.lower() or "generic" in r.lower()
                   for r in result.filter_reasons)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
