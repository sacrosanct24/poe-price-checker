"""
Tests for core/build_archetypes/archetype_matcher.py

Tests the archetype matching and scoring functionality.
"""
import pytest
from unittest.mock import MagicMock

from core.build_archetypes.archetype_matcher import (
    ArchetypeMatcher,
    get_archetype_matcher,
    analyze_item_for_builds,
    get_top_builds_for_item,
    extract_item_stats,
    extract_item_stats_from_dict,
    STAT_PATTERNS,
)
from core.build_archetypes.archetype_database import get_archetype_database
from core.build_archetypes.archetype_models import CrossBuildAnalysis


class TestStatPatterns:
    """Tests for STAT_PATTERNS regex patterns."""

    def test_life_patterns(self):
        """Life patterns match correctly."""
        assert "maximum_life" in STAT_PATTERNS
        patterns = STAT_PATTERNS["maximum_life"]
        assert len(patterns) > 0

    def test_resistance_patterns(self):
        """Resistance patterns exist."""
        assert "fire_resistance" in STAT_PATTERNS
        assert "cold_resistance" in STAT_PATTERNS
        assert "lightning_resistance" in STAT_PATTERNS
        assert "chaos_resistance" in STAT_PATTERNS

    def test_damage_patterns(self):
        """Damage patterns exist."""
        assert "physical_damage" in STAT_PATTERNS
        assert "fire_damage" in STAT_PATTERNS
        assert "spell_damage" in STAT_PATTERNS

    def test_minion_patterns(self):
        """Minion patterns exist."""
        assert "minion_damage" in STAT_PATTERNS
        assert "minion_life" in STAT_PATTERNS


class TestExtractItemStats:
    """Tests for extract_item_stats function."""

    @pytest.fixture
    def mock_item_with_life(self):
        """Create mock item with life mod."""
        item = MagicMock()
        item.explicit_mods = ["+92 to Maximum Life"]
        item.implicit_mods = []
        item.crafted_mods = []
        item.fractured_mods = []
        return item

    @pytest.fixture
    def mock_item_multi_mod(self):
        """Create mock item with multiple mods."""
        item = MagicMock()
        item.explicit_mods = [
            "+92 to Maximum Life",
            "+40% to Fire Resistance",
            "+30% to Cold Resistance",
            "15% increased Attack Speed",
        ]
        item.implicit_mods = ["+25% to Cold Resistance"]
        item.crafted_mods = []
        item.fractured_mods = []
        return item

    def test_extracts_life(self, mock_item_with_life):
        """Extracts life stat from item."""
        stats = extract_item_stats(mock_item_with_life)
        assert "maximum_life" in stats
        assert stats["maximum_life"] == 92

    def test_extracts_multiple_stats(self, mock_item_multi_mod):
        """Extracts multiple stats from item."""
        stats = extract_item_stats(mock_item_multi_mod)
        assert "maximum_life" in stats
        assert "fire_resistance" in stats
        assert "attack_speed" in stats

    def test_accumulates_same_stat(self, mock_item_multi_mod):
        """Accumulates same stat from different sources."""
        stats = extract_item_stats(mock_item_multi_mod)
        # Cold res from explicit + implicit
        assert stats["cold_resistance"] == 55  # 30 + 25

    def test_handles_empty_item(self):
        """Handles item with no mods."""
        item = MagicMock()
        item.explicit_mods = []
        item.implicit_mods = []
        item.crafted_mods = []
        item.fractured_mods = []
        stats = extract_item_stats(item)
        assert stats == {}


class TestExtractItemStatsFromDict:
    """Tests for extract_item_stats_from_dict function."""

    def test_extracts_from_dict(self):
        """Extracts stats from dictionary format."""
        item_data = {
            "explicit_mods": ["+80 to Maximum Life", "+35% to Fire Resistance"],
            "implicit_mods": [],
        }
        stats = extract_item_stats_from_dict(item_data)
        assert stats["maximum_life"] == 80
        assert stats["fire_resistance"] == 35

    def test_handles_missing_keys(self):
        """Handles dict with missing mod keys."""
        item_data = {"explicit_mods": ["+50 to Maximum Life"]}
        stats = extract_item_stats_from_dict(item_data)
        assert stats["maximum_life"] == 50

    def test_handles_empty_dict(self):
        """Handles empty dict."""
        stats = extract_item_stats_from_dict({})
        assert stats == {}


class TestArchetypeMatcher:
    """Tests for ArchetypeMatcher class."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return ArchetypeMatcher()

    @pytest.fixture
    def rf_item_stats(self):
        """Stats for an RF-friendly item."""
        return {
            "maximum_life": 95,
            "fire_resistance": 42,
            "life_regeneration_rate": 3.5,
            "armour": 400,
            "fire_damage_over_time_multiplier": 15,
        }

    @pytest.fixture
    def minion_item_stats(self):
        """Stats for a minion-friendly item."""
        return {
            "maximum_life": 70,
            "minion_damage": 30,
            "minion_life": 20,
            "minion_attack_speed": 10,
        }

    @pytest.fixture
    def crit_item_stats(self):
        """Stats for a crit-focused item."""
        return {
            "maximum_life": 60,
            "critical_strike_chance": 35,
            "critical_strike_multiplier": 25,
            "attack_speed": 12,
        }

    def test_match_stats_returns_analysis(self, matcher, rf_item_stats):
        """match_stats returns CrossBuildAnalysis."""
        result = matcher.match_stats(rf_item_stats, "Test Ring")
        assert isinstance(result, CrossBuildAnalysis)
        assert result.item_name == "Test Ring"
        assert len(result.matches) > 0

    def test_rf_item_matches_rf_build(self, matcher, rf_item_stats):
        """RF item matches RF Juggernaut."""
        result = matcher.match_stats(rf_item_stats, "RF Ring")
        top_matches = result.get_top_matches(5)
        archetype_names = [m.archetype.name for m in top_matches]
        # RF Juggernaut should be in top matches
        assert "RF Juggernaut" in archetype_names

    def test_minion_item_matches_minion_builds(self, matcher, minion_item_stats):
        """Minion item matches minion builds."""
        result = matcher.match_stats(minion_item_stats, "Minion Helm")
        top_matches = result.get_top_matches(5)
        # Should match SRS, Skeleton Mages, etc.
        categories = [m.archetype.category.value for m in top_matches]
        assert "minion" in categories

    def test_min_score_filtering(self, matcher, rf_item_stats):
        """min_score filters out low matches."""
        result_low = matcher.match_stats(rf_item_stats, min_score=0)
        result_high = matcher.match_stats(rf_item_stats, min_score=50)
        assert len(result_high.matches) <= len(result_low.matches)
        for match in result_high.matches:
            assert match.score >= 50

    def test_missing_required_stats_zero_score(self, matcher):
        """Missing required stats results in zero score."""
        # TS Deadeye requires crit
        stats = {"maximum_life": 100, "cold_damage": 50}
        result = matcher.match_stats(stats)
        ts_match = None
        for m in result.matches:
            if m.archetype.id == "ts_deadeye":
                ts_match = m
                break
        if ts_match:
            assert ts_match.score == 0
            assert len(ts_match.missing_required) > 0

    def test_match_item_dict(self, matcher):
        """match_item_dict works with dictionary data."""
        item_data = {
            "name": "Test Amulet",
            "explicit_mods": [
                "+80 to Maximum Life",
                "+35% to Fire Resistance",
            ],
        }
        result = matcher.match_item_dict(item_data)
        assert result.item_name == "Test Amulet"
        assert len(result.matches) > 0

    def test_get_builds_for_stat(self, matcher):
        """get_builds_for_stat returns builds using that stat."""
        life_builds = matcher.get_builds_for_stat("maximum_life")
        assert len(life_builds) > 0
        # Life should be valued by most builds
        assert len(life_builds) > 10

        minion_builds = matcher.get_builds_for_stat("minion_damage")
        assert len(minion_builds) > 0
        # Only minion builds should value minion damage
        assert len(minion_builds) < len(life_builds)


class TestGetArchetypeMatcher:
    """Tests for get_archetype_matcher singleton."""

    def test_returns_matcher(self):
        """get_archetype_matcher returns an ArchetypeMatcher."""
        matcher = get_archetype_matcher()
        assert isinstance(matcher, ArchetypeMatcher)

    def test_singleton_behavior(self):
        """get_archetype_matcher returns same instance."""
        m1 = get_archetype_matcher()
        m2 = get_archetype_matcher()
        assert m1 is m2


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def mock_item(self):
        """Create mock parsed item."""
        item = MagicMock()
        item.name = "Test Item"
        item.explicit_mods = ["+90 to Maximum Life", "+40% to Fire Resistance"]
        item.implicit_mods = []
        item.crafted_mods = []
        item.fractured_mods = []
        return item

    def test_analyze_item_for_builds(self, mock_item):
        """analyze_item_for_builds works correctly."""
        result = analyze_item_for_builds(mock_item)
        assert isinstance(result, CrossBuildAnalysis)

    def test_analyze_item_for_builds_with_min_score(self, mock_item):
        """analyze_item_for_builds respects min_score."""
        result = analyze_item_for_builds(mock_item, min_score=50)
        for match in result.matches:
            assert match.score >= 50

    def test_get_top_builds_for_item(self, mock_item):
        """get_top_builds_for_item returns top matches."""
        matches = get_top_builds_for_item(mock_item, limit=3)
        assert len(matches) <= 3
        # Should be sorted by score
        scores = [m.score for m in matches]
        assert scores == sorted(scores, reverse=True)


class TestScoringAlgorithm:
    """Tests for the scoring algorithm behavior."""

    @pytest.fixture
    def matcher(self):
        """Create matcher instance."""
        return ArchetypeMatcher()

    def test_more_stats_higher_score(self, matcher):
        """More matching stats = higher score."""
        minimal = {"maximum_life": 80}
        better = {"maximum_life": 80, "fire_resistance": 40}
        best = {"maximum_life": 80, "fire_resistance": 40, "armour": 300}

        r1 = matcher.match_stats(minimal)
        r2 = matcher.match_stats(better)
        r3 = matcher.match_stats(best)

        # Get RF Juggernaut scores
        def get_rf_score(result):
            for m in result.matches:
                if m.archetype.id == "rf_juggernaut":
                    return m.score
            return 0

        assert get_rf_score(r2) >= get_rf_score(r1)
        assert get_rf_score(r3) >= get_rf_score(r2)

    def test_higher_values_higher_score(self, matcher):
        """Higher stat values = higher score."""
        low = {"maximum_life": 50}
        high = {"maximum_life": 100}

        r1 = matcher.match_stats(low)
        r2 = matcher.match_stats(high)

        # Compare best match scores
        assert r2.best_match.score >= r1.best_match.score

    def test_weighted_stats_matter_more(self, matcher):
        """Higher weight stats contribute more to score."""
        # RF Jugg values life regen highly
        # Both need life since it's required
        life_only = {"maximum_life": 100}
        life_and_regen = {"maximum_life": 100, "life_regeneration_rate": 5.0}

        r1 = matcher.match_stats(life_only)
        r2 = matcher.match_stats(life_and_regen)

        def get_rf_score(result):
            for m in result.matches:
                if m.archetype.id == "rf_juggernaut":
                    return m.score
            return 0

        # Life alone should give a score
        rf1 = get_rf_score(r1)
        # Life + regen should give higher score
        rf2 = get_rf_score(r2)
        assert rf1 > 0
        assert rf2 > rf1  # Adding regen improves score
