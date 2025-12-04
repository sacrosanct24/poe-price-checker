"""Tests for core/smart_trade_filters.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestFilterPriority:
    """Tests for FilterPriority dataclass."""

    def test_creation(self):
        """Test creating FilterPriority."""
        from core.smart_trade_filters import FilterPriority

        fp = FilterPriority(
            stat_id="pseudo.pseudo_total_life",
            min_value=60,
            max_value=100,
            priority=10,
            reason="Life build",
            is_critical=True,
        )

        assert fp.stat_id == "pseudo.pseudo_total_life"
        assert fp.min_value == 60
        assert fp.max_value == 100
        assert fp.priority == 10
        assert fp.reason == "Life build"
        assert fp.is_critical is True

    def test_defaults(self):
        """Test FilterPriority default values."""
        from core.smart_trade_filters import FilterPriority

        fp = FilterPriority(stat_id="test")

        assert fp.stat_id == "test"
        assert fp.min_value is None
        assert fp.max_value is None
        assert fp.priority == 0
        assert fp.reason == ""
        assert fp.is_critical is False


class TestSmartFilterResult:
    """Tests for SmartFilterResult dataclass."""

    def test_creation(self):
        """Test creating SmartFilterResult."""
        from core.smart_trade_filters import SmartFilterResult, FilterPriority

        result = SmartFilterResult(
            filters=[
                FilterPriority(stat_id="life", min_value=60, priority=10),
                FilterPriority(stat_id="res", min_value=40, priority=20),
            ],
            archetype_summary="Life Attack",
            gap_summary="Fire: 20%",
            filter_reasons=["Need life", "Need res"],
        )

        assert len(result.filters) == 2
        assert result.archetype_summary == "Life Attack"
        assert result.gap_summary == "Fire: 20%"
        assert len(result.filter_reasons) == 2

    def test_defaults(self):
        """Test SmartFilterResult default values."""
        from core.smart_trade_filters import SmartFilterResult

        result = SmartFilterResult()

        assert result.filters == []
        assert result.archetype_summary == ""
        assert result.gap_summary == ""
        assert result.filter_reasons == []

    def test_to_trade_filters_basic(self):
        """Test to_trade_filters with basic filters."""
        from core.smart_trade_filters import SmartFilterResult, FilterPriority

        result = SmartFilterResult(
            filters=[
                FilterPriority(stat_id="life", min_value=60, priority=10),
                FilterPriority(stat_id="res", min_value=40, priority=5),
            ]
        )

        trade_filters = result.to_trade_filters()

        assert len(trade_filters) == 2
        # Lower priority should come first
        assert trade_filters[0]["id"] == "res"
        assert trade_filters[0]["value"]["min"] == 40
        assert trade_filters[1]["id"] == "life"

    def test_to_trade_filters_with_max_value(self):
        """Test to_trade_filters with max_value."""
        from core.smart_trade_filters import SmartFilterResult, FilterPriority

        result = SmartFilterResult(
            filters=[
                FilterPriority(stat_id="test", min_value=10, max_value=50),
            ]
        )

        trade_filters = result.to_trade_filters()

        assert len(trade_filters) == 1
        assert trade_filters[0]["value"]["min"] == 10
        assert trade_filters[0]["value"]["max"] == 50

    def test_to_trade_filters_no_value(self):
        """Test to_trade_filters with no min/max values."""
        from core.smart_trade_filters import SmartFilterResult, FilterPriority

        result = SmartFilterResult(
            filters=[
                FilterPriority(stat_id="test"),
            ]
        )

        trade_filters = result.to_trade_filters()

        assert len(trade_filters) == 1
        assert trade_filters[0]["id"] == "test"
        assert "value" not in trade_filters[0]

    def test_to_trade_filters_respects_limit(self):
        """Test to_trade_filters respects max_filters."""
        from core.smart_trade_filters import SmartFilterResult, FilterPriority

        result = SmartFilterResult(
            filters=[
                FilterPriority(stat_id=f"stat{i}", priority=i)
                for i in range(10)
            ]
        )

        trade_filters = result.to_trade_filters(max_filters=3)

        assert len(trade_filters) == 3
        # Should get the lowest priority (most important) ones
        assert trade_filters[0]["id"] == "stat0"
        assert trade_filters[1]["id"] == "stat1"
        assert trade_filters[2]["id"] == "stat2"

    def test_to_trade_filters_sorts_by_priority(self):
        """Test to_trade_filters sorts by priority."""
        from core.smart_trade_filters import SmartFilterResult, FilterPriority

        result = SmartFilterResult(
            filters=[
                FilterPriority(stat_id="low", priority=30),
                FilterPriority(stat_id="high", priority=0),
                FilterPriority(stat_id="medium", priority=15),
            ]
        )

        trade_filters = result.to_trade_filters()

        assert trade_filters[0]["id"] == "high"
        assert trade_filters[1]["id"] == "medium"
        assert trade_filters[2]["id"] == "low"


class TestSmartFilterBuilderInit:
    """Tests for SmartFilterBuilder initialization."""

    def test_init_no_params(self):
        """Test initialization without parameters."""
        from core.smart_trade_filters import SmartFilterBuilder

        builder = SmartFilterBuilder()

        assert builder.archetype is None
        assert builder.build_stats is None
        assert builder.upgrade_calculator is None

    def test_init_with_archetype(self):
        """Test initialization with archetype."""
        from core.smart_trade_filters import SmartFilterBuilder

        mock_archetype = MagicMock()
        builder = SmartFilterBuilder(archetype=mock_archetype)

        assert builder.archetype is mock_archetype

    def test_init_with_build_stats(self):
        """Test initialization with build_stats creates upgrade_calculator."""
        from core.smart_trade_filters import SmartFilterBuilder

        mock_stats = MagicMock()

        with patch('core.smart_trade_filters.UpgradeCalculator') as mock_calc_class:
            builder = SmartFilterBuilder(build_stats=mock_stats)

            mock_calc_class.assert_called_once_with(mock_stats)
            assert builder.upgrade_calculator is not None


class TestSmartFilterBuilderPriorityConstants:
    """Tests for priority constants."""

    def test_priority_ordering(self):
        """Test priority constants are in correct order."""
        from core.smart_trade_filters import SmartFilterBuilder

        # Lower number = higher priority
        assert SmartFilterBuilder.PRIORITY_CRITICAL < SmartFilterBuilder.PRIORITY_HIGH
        assert SmartFilterBuilder.PRIORITY_HIGH < SmartFilterBuilder.PRIORITY_MEDIUM
        assert SmartFilterBuilder.PRIORITY_MEDIUM < SmartFilterBuilder.PRIORITY_LOW


class TestSmartFilterBuilderBuildFilters:
    """Tests for build_filters method."""

    def test_build_filters_empty(self):
        """Test build_filters with no context."""
        from core.smart_trade_filters import SmartFilterBuilder

        builder = SmartFilterBuilder()
        result = builder.build_filters()

        assert result is not None
        # Should have default filters
        assert len(result.filters) > 0

    def test_build_filters_with_archetype(self):
        """Test build_filters with archetype."""
        from core.smart_trade_filters import SmartFilterBuilder
        from core.build_archetype import DefenseType, AttackType

        mock_archetype = MagicMock()
        mock_archetype.defense_type = DefenseType.LIFE
        mock_archetype.attack_type = AttackType.ATTACK
        mock_archetype.is_crit = False
        mock_archetype.needs_strength = False
        mock_archetype.needs_dexterity = False
        mock_archetype.needs_intelligence = False
        mock_archetype.get_summary.return_value = "Life Attack Build"

        builder = SmartFilterBuilder(archetype=mock_archetype)

        with patch.object(builder, '_get_stat_id', return_value="pseudo.pseudo_total_life"):
            result = builder.build_filters()

        assert result.archetype_summary == "Life Attack Build"

    def test_build_filters_with_slot(self):
        """Test build_filters with slot parameter."""
        from core.smart_trade_filters import SmartFilterBuilder

        builder = SmartFilterBuilder()

        with patch.object(builder, '_get_stat_id', return_value="test_stat"):
            result = builder.build_filters(slot="Boots")

        # Should include movement speed filter for boots
        assert any("movement" in f.reason.lower() for f in result.filters)


class TestSmartFilterBuilderAddGapFilters:
    """Tests for _add_gap_filters method."""

    def test_add_gap_filters_no_calculator(self):
        """Test _add_gap_filters does nothing without calculator."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()
        result = SmartFilterResult()

        builder._add_gap_filters(result)

        # No filters should be added
        assert len(result.filters) == 0

    def test_add_gap_filters_fire_res(self):
        """Test _add_gap_filters adds fire resistance filter."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()

        # Mock upgrade calculator with fire res gap
        mock_calc = MagicMock()
        mock_gaps = MagicMock()
        mock_gaps.fire_gap = 30
        mock_gaps.cold_gap = 0
        mock_gaps.lightning_gap = 0
        mock_gaps.chaos_gap = 0
        mock_calc.calculate_resistance_gaps.return_value = mock_gaps
        builder.upgrade_calculator = mock_calc

        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="fire_res_id"):
            builder._add_gap_filters(result)

        assert len(result.filters) == 1
        assert result.filters[0].stat_id == "fire_res_id"
        assert result.filters[0].min_value == 30
        assert result.filters[0].is_critical is True

    def test_add_gap_filters_multiple_gaps(self):
        """Test _add_gap_filters adds multiple gap filters."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()

        mock_calc = MagicMock()
        mock_gaps = MagicMock()
        mock_gaps.fire_gap = 20
        mock_gaps.cold_gap = 15
        mock_gaps.lightning_gap = 10
        mock_gaps.chaos_gap = 50  # High enough to trigger chaos filter
        mock_calc.calculate_resistance_gaps.return_value = mock_gaps
        builder.upgrade_calculator = mock_calc

        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="res_id"):
            builder._add_gap_filters(result)

        # Should have fire, cold, lightning, and chaos filters
        assert len(result.filters) == 4

    def test_add_gap_filters_caps_values(self):
        """Test _add_gap_filters caps resistance values."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()

        mock_calc = MagicMock()
        mock_gaps = MagicMock()
        mock_gaps.fire_gap = 100  # Very high gap
        mock_gaps.cold_gap = 0
        mock_gaps.lightning_gap = 0
        mock_gaps.chaos_gap = 0
        mock_calc.calculate_resistance_gaps.return_value = mock_gaps
        builder.upgrade_calculator = mock_calc

        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="fire_res"):
            builder._add_gap_filters(result)

        # Should cap at 45
        assert result.filters[0].min_value == 45


class TestSmartFilterBuilderAddArchetypeFilters:
    """Tests for _add_archetype_filters method."""

    def test_add_archetype_filters_no_archetype(self):
        """Test _add_archetype_filters calls default when no archetype."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()
        result = SmartFilterResult()

        with patch.object(builder, '_add_default_filters') as mock_default:
            builder._add_archetype_filters(result)
            mock_default.assert_called_once_with(result)

    def test_add_archetype_filters_life_build(self):
        """Test _add_archetype_filters for life build."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult
        from core.build_archetype import DefenseType, AttackType

        mock_archetype = MagicMock()
        mock_archetype.defense_type = DefenseType.LIFE
        mock_archetype.attack_type = AttackType.ATTACK
        mock_archetype.is_crit = False
        mock_archetype.needs_strength = False
        mock_archetype.needs_dexterity = False
        mock_archetype.needs_intelligence = False

        builder = SmartFilterBuilder(archetype=mock_archetype)
        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="life_id"):
            builder._add_archetype_filters(result)

        # Should have life filter
        life_filters = [f for f in result.filters if "life" in f.reason.lower()]
        assert len(life_filters) > 0

    def test_add_archetype_filters_es_build(self):
        """Test _add_archetype_filters for ES build."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult
        from core.build_archetype import DefenseType, AttackType

        mock_archetype = MagicMock()
        mock_archetype.defense_type = DefenseType.ENERGY_SHIELD
        mock_archetype.attack_type = AttackType.SPELL
        mock_archetype.is_crit = False
        mock_archetype.needs_strength = False
        mock_archetype.needs_dexterity = False
        mock_archetype.needs_intelligence = True

        builder = SmartFilterBuilder(archetype=mock_archetype)
        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="es_id"):
            builder._add_archetype_filters(result)

        # Should have ES filter
        es_filters = [f for f in result.filters if "es" in f.reason.lower()]
        assert len(es_filters) > 0

    def test_add_archetype_filters_crit_build(self):
        """Test _add_archetype_filters for crit build."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult
        from core.build_archetype import DefenseType, AttackType

        mock_archetype = MagicMock()
        mock_archetype.defense_type = DefenseType.LIFE
        mock_archetype.attack_type = AttackType.ATTACK
        mock_archetype.is_crit = True
        mock_archetype.needs_strength = False
        mock_archetype.needs_dexterity = False
        mock_archetype.needs_intelligence = False

        builder = SmartFilterBuilder(archetype=mock_archetype)
        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="crit_id"):
            builder._add_archetype_filters(result)

        # Should have crit filter
        crit_filters = [f for f in result.filters if "crit" in f.reason.lower()]
        assert len(crit_filters) > 0


class TestSmartFilterBuilderAddSlotFilters:
    """Tests for _add_slot_filters method."""

    def test_add_slot_filters_boots(self):
        """Test _add_slot_filters for boots."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()
        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="ms_id"):
            builder._add_slot_filters(result, "Boots")

        # Should have movement speed filter
        assert len(result.filters) == 1
        assert "movement" in result.filters[0].reason.lower()

    def test_add_slot_filters_gloves_attack(self):
        """Test _add_slot_filters for gloves with attack build."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult
        from core.build_archetype import AttackType

        mock_archetype = MagicMock()
        mock_archetype.attack_type = AttackType.ATTACK

        builder = SmartFilterBuilder(archetype=mock_archetype)
        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="as_id"):
            builder._add_slot_filters(result, "Gloves")

        # Should have attack speed filter
        assert len(result.filters) == 1
        assert "attack" in result.filters[0].reason.lower()

    def test_add_slot_filters_other_slot(self):
        """Test _add_slot_filters for non-special slot."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()
        result = SmartFilterResult()

        builder._add_slot_filters(result, "Helmet")

        # No special filters for helmet
        assert len(result.filters) == 0


class TestSmartFilterBuilderAddDefaultFilters:
    """Tests for _add_default_filters method."""

    def test_add_default_filters(self):
        """Test _add_default_filters adds life and resistances."""
        from core.smart_trade_filters import SmartFilterBuilder, SmartFilterResult

        builder = SmartFilterBuilder()
        result = SmartFilterResult()

        with patch.object(builder, '_get_stat_id', return_value="stat_id"):
            builder._add_default_filters(result)

        # Should have default filters
        assert len(result.filters) >= 1
        # The reason text says "No archetype" not "Default"
        assert any("no archetype" in r.lower() for r in result.filter_reasons)


class TestSmartFilterBuilderGetStatId:
    """Tests for _get_stat_id method."""

    def test_get_stat_id_found(self):
        """Test _get_stat_id when stat is found."""
        from core.smart_trade_filters import SmartFilterBuilder

        builder = SmartFilterBuilder()

        with patch('core.smart_trade_filters.get_stat_id', return_value=("stat_id", "stat_name")):
            result = builder._get_stat_id("life")

        assert result == "stat_id"

    def test_get_stat_id_not_found(self):
        """Test _get_stat_id when stat is not found."""
        from core.smart_trade_filters import SmartFilterBuilder

        builder = SmartFilterBuilder()

        with patch('core.smart_trade_filters.get_stat_id', return_value=None):
            result = builder._get_stat_id("unknown")

        assert result is None


class TestBuildSmartFiltersFunction:
    """Tests for build_smart_filters convenience function."""

    def test_build_smart_filters_basic(self):
        """Test build_smart_filters basic usage."""
        from core.smart_trade_filters import build_smart_filters

        with patch('core.smart_trade_filters.SmartFilterBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_result = MagicMock()
            mock_result.to_trade_filters.return_value = [{"id": "test"}]
            mock_builder.build_filters.return_value = mock_result
            mock_builder_class.return_value = mock_builder

            filters, result = build_smart_filters()

            assert filters == [{"id": "test"}]
            assert result is mock_result

    def test_build_smart_filters_with_params(self):
        """Test build_smart_filters with parameters."""
        from core.smart_trade_filters import build_smart_filters

        mock_archetype = MagicMock()
        mock_stats = MagicMock()

        with patch('core.smart_trade_filters.SmartFilterBuilder') as mock_builder_class:
            mock_builder = MagicMock()
            mock_result = MagicMock()
            mock_result.to_trade_filters.return_value = []
            mock_builder.build_filters.return_value = mock_result
            mock_builder_class.return_value = mock_builder

            filters, result = build_smart_filters(
                archetype=mock_archetype,
                build_stats=mock_stats,
                slot="Boots",
                max_filters=4,
            )

            mock_builder_class.assert_called_once_with(mock_archetype, mock_stats)
            mock_builder.build_filters.assert_called_once_with(slot="Boots")
            mock_result.to_trade_filters.assert_called_once_with(max_filters=4)
