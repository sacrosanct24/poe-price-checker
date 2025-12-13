"""
Tests for core/build_archetypes/archetype_models.py

Tests the archetype model dataclasses and enums.
"""
import pytest

from core.build_archetypes.archetype_models import (
    BuildArchetype,
    BuildCategory,
    DamageType,
    DefenseType,
    StatWeight,
    ArchetypeMatch,
    CrossBuildAnalysis,
)


class TestBuildCategory:
    """Tests for BuildCategory enum."""

    def test_all_categories_exist(self):
        """All expected categories exist."""
        assert BuildCategory.ATTACK
        assert BuildCategory.SPELL
        assert BuildCategory.MINION
        assert BuildCategory.DOT
        assert BuildCategory.TOTEM_TRAP_MINE
        assert BuildCategory.AURA_SUPPORT

    def test_category_values(self):
        """Categories have expected string values."""
        assert BuildCategory.ATTACK.value == "attack"
        assert BuildCategory.SPELL.value == "spell"
        assert BuildCategory.DOT.value == "dot"


class TestDamageType:
    """Tests for DamageType enum."""

    def test_all_damage_types_exist(self):
        """All expected damage types exist."""
        assert DamageType.PHYSICAL
        assert DamageType.FIRE
        assert DamageType.COLD
        assert DamageType.LIGHTNING
        assert DamageType.CHAOS
        assert DamageType.ELEMENTAL

    def test_damage_type_values(self):
        """Damage types have expected string values."""
        assert DamageType.FIRE.value == "fire"
        assert DamageType.CHAOS.value == "chaos"


class TestDefenseType:
    """Tests for DefenseType enum."""

    def test_all_defense_types_exist(self):
        """All expected defense types exist."""
        assert DefenseType.LIFE
        assert DefenseType.ENERGY_SHIELD
        assert DefenseType.HYBRID
        assert DefenseType.EVASION
        assert DefenseType.ARMOUR
        assert DefenseType.BLOCK
        assert DefenseType.LOW_LIFE


class TestStatWeight:
    """Tests for StatWeight dataclass."""

    def test_basic_creation(self):
        """StatWeight creates with basic params."""
        sw = StatWeight(stat_name="maximum_life", weight=2.0)
        assert sw.stat_name == "maximum_life"
        assert sw.weight == 2.0

    def test_with_thresholds(self):
        """StatWeight can have thresholds."""
        sw = StatWeight(
            stat_name="fire_resistance",
            weight=1.5,
            min_threshold=40.0,
            ideal_value=75.0,
        )
        assert sw.min_threshold == 40.0
        assert sw.ideal_value == 75.0

    def test_defaults(self):
        """StatWeight has sensible defaults."""
        sw = StatWeight(stat_name="test")
        assert sw.weight == 1.0
        assert sw.min_threshold is None
        assert sw.ideal_value is None


class TestBuildArchetype:
    """Tests for BuildArchetype dataclass."""

    @pytest.fixture
    def sample_archetype(self):
        """Create a sample archetype for testing."""
        return BuildArchetype(
            id="test_build",
            name="Test Build",
            description="A test build for unit tests",
            category=BuildCategory.ATTACK,
            ascendancy="Slayer",
            damage_types=[DamageType.PHYSICAL],
            defense_types=[DefenseType.LIFE, DefenseType.ARMOUR],
            key_stats=[
                StatWeight(stat_name="maximum_life", weight=2.0),
                StatWeight(stat_name="physical_damage", weight=1.8),
            ],
            required_stats={"maximum_life"},
            popularity=0.05,
            tags=["melee", "tanky"],
            league_starter=True,
            ssf_viable=True,
            budget_tier=1,
        )

    def test_basic_creation(self, sample_archetype):
        """BuildArchetype creates successfully."""
        assert sample_archetype.id == "test_build"
        assert sample_archetype.name == "Test Build"
        assert sample_archetype.category == BuildCategory.ATTACK

    def test_get_stat_weight(self, sample_archetype):
        """get_stat_weight returns correct weights."""
        assert sample_archetype.get_stat_weight("maximum_life") == 2.0
        assert sample_archetype.get_stat_weight("physical_damage") == 1.8
        assert sample_archetype.get_stat_weight("unknown_stat") == 0.0

    def test_is_key_stat(self, sample_archetype):
        """is_key_stat identifies key stats correctly."""
        assert sample_archetype.is_key_stat("maximum_life") is True
        assert sample_archetype.is_key_stat("physical_damage") is True
        assert sample_archetype.is_key_stat("fire_damage") is False

    def test_defaults(self):
        """BuildArchetype has sensible defaults."""
        arch = BuildArchetype(
            id="minimal",
            name="Minimal",
            description="Minimal test",
            category=BuildCategory.SPELL,
            ascendancy="Inquisitor",
        )
        assert arch.damage_types == []
        assert arch.defense_types == []
        assert arch.key_stats == []
        assert arch.required_stats == set()
        assert arch.popularity == 0.05
        assert arch.league_starter is False
        assert arch.budget_tier == 2


class TestArchetypeMatch:
    """Tests for ArchetypeMatch dataclass."""

    @pytest.fixture
    def sample_archetype(self):
        """Create a sample archetype for testing."""
        return BuildArchetype(
            id="test",
            name="Test",
            description="Test",
            category=BuildCategory.ATTACK,
            ascendancy="Slayer",
        )

    def test_basic_creation(self, sample_archetype):
        """ArchetypeMatch creates successfully."""
        match = ArchetypeMatch(
            archetype=sample_archetype,
            score=75.0,
            matching_stats=["maximum_life", "physical_damage"],
            missing_required=[],
            reasons=["High life", "Good damage"],
        )
        assert match.score == 75.0
        assert len(match.matching_stats) == 2

    def test_is_strong_match(self, sample_archetype):
        """is_strong_match returns correct value."""
        strong = ArchetypeMatch(archetype=sample_archetype, score=80.0)
        weak = ArchetypeMatch(archetype=sample_archetype, score=50.0)
        assert strong.is_strong_match is True
        assert weak.is_strong_match is False

    def test_is_moderate_match(self, sample_archetype):
        """is_moderate_match returns correct value."""
        moderate = ArchetypeMatch(archetype=sample_archetype, score=60.0)
        strong = ArchetypeMatch(archetype=sample_archetype, score=80.0)
        weak = ArchetypeMatch(archetype=sample_archetype, score=30.0)
        assert moderate.is_moderate_match is True
        assert strong.is_moderate_match is False
        assert weak.is_moderate_match is False

    def test_match_summary(self, sample_archetype):
        """match_summary returns correct labels."""
        assert ArchetypeMatch(archetype=sample_archetype, score=95).match_summary == "Excellent"
        assert ArchetypeMatch(archetype=sample_archetype, score=75).match_summary == "Strong"
        assert ArchetypeMatch(archetype=sample_archetype, score=55).match_summary == "Moderate"
        assert ArchetypeMatch(archetype=sample_archetype, score=35).match_summary == "Weak"
        assert ArchetypeMatch(archetype=sample_archetype, score=15).match_summary == "Poor"


class TestCrossBuildAnalysis:
    """Tests for CrossBuildAnalysis dataclass."""

    @pytest.fixture
    def sample_archetypes(self):
        """Create sample archetypes for testing."""
        return [
            BuildArchetype(id="a", name="Build A", description="A", category=BuildCategory.ATTACK, ascendancy="Slayer"),
            BuildArchetype(id="b", name="Build B", description="B", category=BuildCategory.SPELL, ascendancy="Inquisitor"),
            BuildArchetype(id="c", name="Build C", description="C", category=BuildCategory.MINION, ascendancy="Necromancer"),
        ]

    @pytest.fixture
    def sample_analysis(self, sample_archetypes):
        """Create a sample analysis for testing."""
        return CrossBuildAnalysis(
            item_name="Test Ring",
            matches=[
                ArchetypeMatch(archetype=sample_archetypes[0], score=85.0),
                ArchetypeMatch(archetype=sample_archetypes[1], score=60.0),
                ArchetypeMatch(archetype=sample_archetypes[2], score=30.0),
            ],
        )

    def test_basic_creation(self, sample_analysis):
        """CrossBuildAnalysis creates successfully."""
        assert sample_analysis.item_name == "Test Ring"
        assert len(sample_analysis.matches) == 3

    def test_best_match(self, sample_analysis):
        """best_match returns highest score."""
        best = sample_analysis.best_match
        assert best is not None
        assert best.score == 85.0
        assert best.archetype.name == "Build A"

    def test_best_match_empty(self):
        """best_match returns None for empty analysis."""
        analysis = CrossBuildAnalysis(item_name="Empty", matches=[])
        assert analysis.best_match is None

    def test_strong_matches(self, sample_analysis):
        """strong_matches returns matches >= 70."""
        strong = sample_analysis.strong_matches
        assert len(strong) == 1
        assert strong[0].score == 85.0

    def test_moderate_matches(self, sample_analysis):
        """moderate_matches returns matches 50-69."""
        moderate = sample_analysis.moderate_matches
        assert len(moderate) == 1
        assert moderate[0].score == 60.0

    def test_get_top_matches(self, sample_analysis):
        """get_top_matches returns top N sorted by score."""
        top2 = sample_analysis.get_top_matches(2)
        assert len(top2) == 2
        assert top2[0].score == 85.0
        assert top2[1].score == 60.0

    def test_summary_strong(self, sample_analysis):
        """summary mentions strong matches when present."""
        assert "Strong fit" in sample_analysis.summary
        assert "Build A" in sample_analysis.summary

    def test_summary_moderate(self, sample_archetypes):
        """summary mentions moderate matches when no strong."""
        analysis = CrossBuildAnalysis(
            item_name="Test",
            matches=[ArchetypeMatch(archetype=sample_archetypes[0], score=55.0)],
        )
        assert "Moderate fit" in analysis.summary

    def test_summary_none(self, sample_archetypes):
        """summary indicates no matches when scores low."""
        analysis = CrossBuildAnalysis(
            item_name="Test",
            matches=[ArchetypeMatch(archetype=sample_archetypes[0], score=25.0)],
        )
        assert "No strong build matches" in analysis.summary
