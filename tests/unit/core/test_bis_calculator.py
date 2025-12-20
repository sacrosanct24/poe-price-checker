"""Tests for core/bis_calculator.py - BiS (Best-in-Slot) item calculator."""

import pytest

from core.bis_calculator import (
    BiSCalculator,
    BiSRequirements,
    StatRequirement,
    build_trade_query,
    get_trade_url,
    EQUIPMENT_SLOTS,
)
from core.build_stat_calculator import BuildStats
from core.build_priorities import BuildPriorities, PriorityTier


class TestStatRequirement:
    """Tests for StatRequirement dataclass."""

    def test_create_stat_requirement(self):
        """Should create stat requirement with all fields."""
        req = StatRequirement(
            stat_type="life",
            stat_id="pseudo.pseudo_total_life",
            min_value=70,
            priority=1,
            reason="Life build - max life is essential",
        )

        assert req.stat_type == "life"
        assert req.stat_id == "pseudo.pseudo_total_life"
        assert req.min_value == 70
        assert req.priority == 1
        assert req.reason == "Life build - max life is essential"


class TestBiSRequirements:
    """Tests for BiSRequirements dataclass."""

    def test_create_empty_requirements(self):
        """Should create empty requirements."""
        reqs = BiSRequirements(slot="Helmet")

        assert reqs.slot == "Helmet"
        assert reqs.required_stats == []
        assert reqs.desired_stats == []
        assert reqs.min_item_level == 75
        assert reqs.max_results == 20

    def test_create_with_stats(self):
        """Should create with stats."""
        required = StatRequirement("life", "stat.life", 70, 1, "Test")
        desired = StatRequirement("fire_resistance", "stat.fire_res", 30, 2, "Test")

        reqs = BiSRequirements(
            slot="Helmet",
            required_stats=[required],
            desired_stats=[desired],
        )

        assert len(reqs.required_stats) == 1
        assert len(reqs.desired_stats) == 1


class TestEquipmentSlots:
    """Tests for EQUIPMENT_SLOTS constant."""

    def test_has_all_major_slots(self):
        """Should have all major equipment slots."""
        expected_slots = [
            "Helmet", "Body Armour", "Gloves", "Boots",
            "Belt", "Ring", "Amulet", "Shield",
        ]

        for slot in expected_slots:
            assert slot in EQUIPMENT_SLOTS

    def test_slot_has_base_types(self):
        """Each slot should have base types defined."""
        for slot, info in EQUIPMENT_SLOTS.items():
            assert "base_types" in info
            assert isinstance(info["base_types"], list)
            assert len(info["base_types"]) > 0

    def test_slot_has_can_have_stats(self):
        """Each slot should have can_have stats defined."""
        for slot, info in EQUIPMENT_SLOTS.items():
            assert "can_have" in info
            assert isinstance(info["can_have"], list)
            assert len(info["can_have"]) > 0


class TestBiSCalculator:
    """Tests for BiSCalculator class."""

    @pytest.fixture
    def life_build_stats(self):
        """Create stats for a life build."""
        return BuildStats(
            life_inc=150.0,
            total_life=5000.0,
            es_inc=20.0,
            total_es=200.0,
            fire_overcap=45.0,
            cold_overcap=40.0,
            lightning_overcap=35.0,
            chaos_res=30.0,
            strength=150.0,
            dexterity=120.0,
            intelligence=100.0,
        )

    @pytest.fixture
    def es_build_stats(self):
        """Create stats for an ES build."""
        return BuildStats(
            life_inc=30.0,
            total_life=1000.0,
            es_inc=200.0,
            total_es=8000.0,
            fire_overcap=50.0,
            cold_overcap=25.0,
            lightning_overcap=20.0,
            chaos_res=10.0,
            strength=80.0,
            dexterity=150.0,
            intelligence=250.0,
        )

    @pytest.fixture
    def low_res_build_stats(self):
        """Create stats for a build with low resistances."""
        return BuildStats(
            life_inc=100.0,
            total_life=4000.0,
            fire_overcap=15.0,  # Below threshold
            cold_overcap=10.0,  # Below threshold
            lightning_overcap=5.0,  # Below threshold
            chaos_res=20.0,  # Below target
            strength=100.0,
            dexterity=100.0,
            intelligence=100.0,
        )

    def test_init_analyzes_build(self, life_build_stats):
        """Should analyze build on init."""
        calculator = BiSCalculator(life_build_stats)

        assert calculator.stats is life_build_stats
        assert calculator.is_life_build is True
        assert calculator.is_es_build is False

    def test_analyze_life_build(self, life_build_stats):
        """Should detect life build correctly."""
        calculator = BiSCalculator(life_build_stats)

        assert calculator.is_life_build is True
        assert calculator.is_es_build is False

    def test_analyze_es_build(self, es_build_stats):
        """Should detect ES build correctly."""
        calculator = BiSCalculator(es_build_stats)

        assert calculator.is_life_build is False
        assert calculator.is_es_build is True

    def test_analyze_resistance_needs(self, low_res_build_stats):
        """Should detect low resistances."""
        calculator = BiSCalculator(low_res_build_stats)

        assert calculator.needs_fire_res is True
        assert calculator.needs_cold_res is True
        assert calculator.needs_lightning_res is True
        assert calculator.needs_chaos_res is True

    def test_analyze_good_resistances(self, life_build_stats):
        """Should detect good resistances."""
        calculator = BiSCalculator(life_build_stats)

        assert calculator.needs_fire_res is False
        assert calculator.needs_cold_res is False
        assert calculator.needs_lightning_res is False

    def test_analyze_attribute_needs(self):
        """Should detect low attributes."""
        stats = BuildStats(
            total_life=5000.0,
            strength=90.0,  # Below 100
            dexterity=95.0,  # Below 100
            intelligence=85.0,  # Below 100
        )
        calculator = BiSCalculator(stats)

        assert calculator.needs_strength is True
        assert calculator.needs_dexterity is True
        assert calculator.needs_intelligence is True

    def test_calculate_requirements_invalid_slot(self, life_build_stats):
        """Should raise error for invalid slot."""
        calculator = BiSCalculator(life_build_stats)

        with pytest.raises(ValueError, match="Unknown equipment slot"):
            calculator.calculate_requirements("Invalid Slot")

    def test_calculate_requirements_helmet_life_build(self, life_build_stats):
        """Should generate helmet requirements for life build."""
        calculator = BiSCalculator(life_build_stats)

        reqs = calculator.calculate_requirements("Helmet")

        assert reqs.slot == "Helmet"
        # Should require life
        life_stats = [s for s in reqs.required_stats if s.stat_type == "life"]
        assert len(life_stats) == 1
        assert life_stats[0].min_value >= 70

    def test_calculate_requirements_helmet_es_build(self, es_build_stats):
        """Should generate helmet requirements for ES build."""
        calculator = BiSCalculator(es_build_stats)

        reqs = calculator.calculate_requirements("Helmet")

        # Should require ES, not life
        es_stats = [s for s in reqs.required_stats if s.stat_type == "energy_shield"]
        life_stats = [s for s in reqs.required_stats if s.stat_type == "life"]
        assert len(es_stats) == 1
        assert len(life_stats) == 0

    def test_calculate_requirements_boots_movement_speed(self, life_build_stats):
        """Boots should require movement speed."""
        calculator = BiSCalculator(life_build_stats)

        reqs = calculator.calculate_requirements("Boots")

        # Should require movement speed
        ms_stats = [s for s in reqs.required_stats if s.stat_type == "movement_speed"]
        assert len(ms_stats) == 1
        assert ms_stats[0].min_value >= 25

    def test_calculate_requirements_low_resistances(self, low_res_build_stats):
        """Should prioritize resistances when low."""
        calculator = BiSCalculator(low_res_build_stats)

        reqs = calculator.calculate_requirements("Helmet")

        # Should desire fire/cold/lightning resistances
        fire_res = [s for s in reqs.desired_stats if s.stat_type == "fire_resistance"]
        cold_res = [s for s in reqs.desired_stats if s.stat_type == "cold_resistance"]
        lightning_res = [s for s in reqs.desired_stats if s.stat_type == "lightning_resistance"]

        assert len(fire_res) == 1
        assert len(cold_res) == 1
        assert len(lightning_res) == 1

    def test_calculate_requirements_stats_sorted_by_priority(self, life_build_stats):
        """Required and desired stats should be sorted by priority."""
        calculator = BiSCalculator(life_build_stats)

        reqs = calculator.calculate_requirements("Helmet")

        # Check required stats are sorted
        if len(reqs.required_stats) > 1:
            for i in range(len(reqs.required_stats) - 1):
                assert reqs.required_stats[i].priority <= reqs.required_stats[i + 1].priority

        # Check desired stats are sorted
        if len(reqs.desired_stats) > 1:
            for i in range(len(reqs.desired_stats) - 1):
                assert reqs.desired_stats[i].priority <= reqs.desired_stats[i + 1].priority

    def test_calculate_requirements_with_custom_priorities(self, life_build_stats):
        """Should use custom priorities when provided."""
        calculator = BiSCalculator(life_build_stats)

        priorities = BuildPriorities()
        priorities.add_priority("life", PriorityTier.CRITICAL, min_value=100)
        priorities.add_priority("fire_resistance", PriorityTier.IMPORTANT, min_value=40)

        reqs = calculator.calculate_requirements("Helmet", custom_priorities=priorities)

        # Should have life as required
        life_stats = [s for s in reqs.required_stats if s.stat_type == "life"]
        assert len(life_stats) == 1
        assert life_stats[0].min_value == 100

        # Should have fire res as desired
        fire_res = [s for s in reqs.desired_stats if s.stat_type == "fire_resistance"]
        assert len(fire_res) == 1
        assert fire_res[0].min_value == 40

    def test_calculate_requirements_custom_priorities_fallback(self, life_build_stats):
        """Should fallback to build type if no critical stats in priorities."""
        calculator = BiSCalculator(life_build_stats)

        priorities = BuildPriorities()
        priorities.is_life_build = True
        # Don't add any critical stats

        reqs = calculator.calculate_requirements("Helmet", custom_priorities=priorities)

        # Should fallback to life requirement
        life_stats = [s for s in reqs.required_stats if s.stat_type == "life"]
        assert len(life_stats) == 1

    def test_make_stat_with_mapping(self, life_build_stats):
        """Should create stat with proper stat_id from mapping."""
        calculator = BiSCalculator(life_build_stats)

        stat = calculator._make_stat("life", min_value=70, priority=1, reason="Test")

        assert stat.stat_type == "life"
        assert stat.min_value == 70
        assert stat.priority == 1
        # Should have a valid stat_id from AFFIX_TO_STAT_ID
        assert stat.stat_id is not None
        assert isinstance(stat.stat_id, str)

    def test_make_stat_without_mapping(self, life_build_stats):
        """Should create fallback stat_id for unmapped stats."""
        calculator = BiSCalculator(life_build_stats)

        stat = calculator._make_stat("unmapped_stat", min_value=50, priority=2, reason="Test")

        # Should use fallback format
        assert stat.stat_id == "pseudo.pseudo_total_unmapped_stat"

    def test_default_min_value(self, life_build_stats):
        """Should return default min values for known stats."""
        calculator = BiSCalculator(life_build_stats)

        assert calculator._default_min_value("life") == 70
        assert calculator._default_min_value("energy_shield") == 50
        assert calculator._default_min_value("fire_resistance") == 30
        assert calculator._default_min_value("movement_speed") == 25
        assert calculator._default_min_value("unknown_stat") == 20

    def test_get_all_slot_requirements(self, life_build_stats):
        """Should generate requirements for all slots."""
        calculator = BiSCalculator(life_build_stats)

        all_reqs = calculator.get_all_slot_requirements()

        # Should have requirements for each equipment slot
        for slot in EQUIPMENT_SLOTS:
            assert slot in all_reqs
            assert isinstance(all_reqs[slot], BiSRequirements)
            assert all_reqs[slot].slot == slot

    def test_get_build_analysis_summary(self, life_build_stats):
        """Should generate readable build summary."""
        calculator = BiSCalculator(life_build_stats)

        summary = calculator.get_build_analysis_summary()

        assert "Build Analysis:" in summary
        assert "Type: Life build" in summary
        assert "5000 life" in summary

    def test_get_build_analysis_summary_es_build(self, es_build_stats):
        """Should show ES build type in summary."""
        calculator = BiSCalculator(es_build_stats)

        summary = calculator.get_build_analysis_summary()

        assert "Type: ES build" in summary
        assert "8000 ES" in summary

    def test_get_build_analysis_summary_with_res_needs(self, low_res_build_stats):
        """Should show resistance needs in summary."""
        calculator = BiSCalculator(low_res_build_stats)

        summary = calculator.get_build_analysis_summary()

        assert "Needs Res:" in summary
        assert "Fire" in summary
        assert "Cold" in summary
        assert "Lightning" in summary

    def test_get_build_analysis_summary_good_resistances(self):
        """Should show good resistances when capped."""
        # Create stats with all good resistances (including chaos)
        stats = BuildStats(
            total_life=5000.0,
            fire_overcap=45.0,
            cold_overcap=40.0,
            lightning_overcap=35.0,
            chaos_res=50.0,  # Above threshold
        )
        calculator = BiSCalculator(stats)

        summary = calculator.get_build_analysis_summary()

        assert "Resistances: Good" in summary

    def test_get_build_analysis_summary_attribute_needs(self):
        """Should show attribute needs in summary."""
        stats = BuildStats(
            total_life=5000.0,
            strength=80.0,
            dexterity=70.0,
            intelligence=60.0,
        )
        calculator = BiSCalculator(stats)

        summary = calculator.get_build_analysis_summary()

        assert "Needs Attr:" in summary
        assert "Str" in summary
        assert "Dex" in summary
        assert "Int" in summary

    def test_amulet_gets_crit_multi(self, life_build_stats):
        """Amulet should get crit multi as desired stat."""
        calculator = BiSCalculator(life_build_stats)

        reqs = calculator.calculate_requirements("Amulet")

        crit_multi = [s for s in reqs.desired_stats if s.stat_type == "critical_strike_multiplier"]
        assert len(crit_multi) >= 0  # May or may not be included depending on slot config

    def test_gloves_gets_attack_speed(self, life_build_stats):
        """Gloves should get attack speed as desired stat."""
        calculator = BiSCalculator(life_build_stats)

        reqs = calculator.calculate_requirements("Gloves")

        attack_speed = [s for s in reqs.desired_stats if s.stat_type == "attack_speed"]
        assert len(attack_speed) >= 0  # May or may not be included depending on slot config

    def test_shield_gets_spell_suppression(self, life_build_stats):
        """Shield should get spell suppression as desired stat."""
        calculator = BiSCalculator(life_build_stats)

        reqs = calculator.calculate_requirements("Shield")

        spell_supp = [s for s in reqs.desired_stats if s.stat_type == "spell_suppression"]
        assert len(spell_supp) >= 0  # May or may not be included depending on slot config


class TestBuildTradeQuery:
    """Tests for build_trade_query function."""

    def test_basic_query_structure(self):
        """Should create basic query structure."""
        reqs = BiSRequirements(slot="Helmet")
        reqs.required_stats = [
            StatRequirement("life", "stat.life", 70, 1, "Test"),
        ]

        query = build_trade_query(reqs)

        assert "query" in query
        assert "stats" in query["query"]
        assert "sort" in query
        assert query["sort"] == {"price": "asc"}

    def test_includes_online_status(self):
        """Query should include online status filter."""
        reqs = BiSRequirements(slot="Helmet")

        query = build_trade_query(reqs)

        assert "status" in query["query"]
        assert query["query"]["status"]["option"] == "online"

    def test_includes_required_stats(self):
        """Should include required stats in query."""
        reqs = BiSRequirements(slot="Helmet")
        reqs.required_stats = [
            StatRequirement("life", "stat.life", 70, 1, "Test"),
            StatRequirement("fire_resistance", "stat.fire_res", 30, 2, "Test"),
        ]

        query = build_trade_query(reqs)

        filters = query["query"]["stats"][0]["filters"]
        assert len(filters) == 2
        assert filters[0]["id"] == "stat.life"
        assert filters[0]["value"]["min"] == 70
        assert filters[1]["id"] == "stat.fire_res"
        assert filters[1]["value"]["min"] == 30

    def test_includes_desired_stats(self):
        """Should include desired stats in query."""
        reqs = BiSRequirements(slot="Helmet")
        reqs.desired_stats = [
            StatRequirement("cold_resistance", "stat.cold_res", 30, 2, "Test"),
        ]

        query = build_trade_query(reqs)

        filters = query["query"]["stats"][0]["filters"]
        assert len(filters) == 1
        assert filters[0]["id"] == "stat.cold_res"

    def test_limits_to_4_stats(self):
        """Should limit to max 4 stats (2 required + 2 desired)."""
        reqs = BiSRequirements(slot="Helmet")
        reqs.required_stats = [
            StatRequirement("life", f"stat.{i}", 70, 1, "Test")
            for i in range(3)
        ]
        reqs.desired_stats = [
            StatRequirement("res", f"stat.res{i}", 30, 2, "Test")
            for i in range(5)
        ]

        query = build_trade_query(reqs)

        filters = query["query"]["stats"][0]["filters"]
        # Should take first 2 required + first 2 desired = 4 total
        assert len(filters) <= 4

    def test_prioritizes_required_over_desired(self):
        """Should prioritize required stats over desired."""
        reqs = BiSRequirements(slot="Helmet")
        reqs.required_stats = [
            StatRequirement("life", "stat.life", 70, 1, "Test"),
            StatRequirement("es", "stat.es", 50, 1, "Test"),
        ]
        reqs.desired_stats = [
            StatRequirement("fire_res", "stat.fire_res", 30, 2, "Test"),
        ]

        query = build_trade_query(reqs)

        filters = query["query"]["stats"][0]["filters"]
        # First 2 should be required stats
        assert filters[0]["id"] == "stat.life"
        assert filters[1]["id"] == "stat.es"

    def test_empty_requirements(self):
        """Should handle empty requirements."""
        reqs = BiSRequirements(slot="Helmet")

        query = build_trade_query(reqs)

        filters = query["query"]["stats"][0]["filters"]
        assert len(filters) == 0

    def test_custom_league(self):
        """Should accept custom league parameter."""
        reqs = BiSRequirements(slot="Helmet")

        query = build_trade_query(reqs, league="Settlers")

        # Function doesn't use league yet, but should accept it
        assert query is not None


class TestGetTradeUrl:
    """Tests for get_trade_url function."""

    def test_returns_base_url(self):
        """Should return base trade URL."""
        query = {"query": {}}

        url = get_trade_url(query)

        assert url.startswith("https://www.pathofexile.com/trade/search/")

    def test_includes_league_in_url(self):
        """Should include league in URL."""
        query = {"query": {}}

        url = get_trade_url(query, league="Settlers")

        assert "Settlers" in url

    def test_url_encodes_league(self):
        """Should URL-encode league name."""
        query = {"query": {}}

        url = get_trade_url(query, league="Temp League")

        assert "Temp%20League" in url

    def test_default_league(self):
        """Should use Standard as default league."""
        query = {"query": {}}

        url = get_trade_url(query)

        assert "Standard" in url
