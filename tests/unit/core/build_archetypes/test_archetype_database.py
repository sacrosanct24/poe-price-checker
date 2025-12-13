"""
Tests for core/build_archetypes/archetype_database.py

Tests the archetype database and lookup functionality.
"""
import pytest

from core.build_archetypes.archetype_database import (
    ArchetypeDatabase,
    get_archetype_database,
    ALL_ARCHETYPES,
)
from core.build_archetypes.archetype_models import (
    BuildCategory,
    DamageType,
    DefenseType,
)


class TestALLArchetypes:
    """Tests for the ALL_ARCHETYPES constant."""

    def test_all_archetypes_not_empty(self):
        """ALL_ARCHETYPES contains archetypes."""
        assert len(ALL_ARCHETYPES) > 0

    def test_all_archetypes_has_expected_count(self):
        """ALL_ARCHETYPES has 20+ archetypes."""
        assert len(ALL_ARCHETYPES) >= 20

    def test_all_archetypes_have_ids(self):
        """All archetypes have unique IDs."""
        ids = [a.id for a in ALL_ARCHETYPES]
        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_all_archetypes_have_names(self):
        """All archetypes have non-empty names."""
        for arch in ALL_ARCHETYPES:
            assert arch.name, f"Archetype {arch.id} has no name"

    def test_popular_builds_present(self):
        """Popular builds are in the database."""
        names = [a.name for a in ALL_ARCHETYPES]
        assert "RF Juggernaut" in names
        assert "Lightning Arrow Deadeye" in names
        assert "SRS Necromancer" in names


class TestArchetypeDatabase:
    """Tests for ArchetypeDatabase class."""

    @pytest.fixture
    def db(self):
        """Get the archetype database."""
        return ArchetypeDatabase()

    def test_get_all(self, db):
        """get_all returns all archetypes."""
        all_archs = db.get_all()
        assert len(all_archs) == len(ALL_ARCHETYPES)

    def test_get_by_id_existing(self, db):
        """get_by_id returns archetype when found."""
        arch = db.get_by_id("rf_juggernaut")
        assert arch is not None
        assert arch.name == "RF Juggernaut"

    def test_get_by_id_not_found(self, db):
        """get_by_id returns None when not found."""
        arch = db.get_by_id("nonexistent_build")
        assert arch is None

    def test_get_by_category(self, db):
        """get_by_category filters by category."""
        attacks = db.get_by_category(BuildCategory.ATTACK)
        assert len(attacks) > 0
        for arch in attacks:
            assert arch.category == BuildCategory.ATTACK

        spells = db.get_by_category(BuildCategory.SPELL)
        assert len(spells) > 0
        for arch in spells:
            assert arch.category == BuildCategory.SPELL

    def test_get_by_damage_type(self, db):
        """get_by_damage_type filters by damage type."""
        fire_builds = db.get_by_damage_type(DamageType.FIRE)
        assert len(fire_builds) > 0
        for arch in fire_builds:
            assert DamageType.FIRE in arch.damage_types

    def test_get_by_defense_type(self, db):
        """get_by_defense_type filters by defense type."""
        life_builds = db.get_by_defense_type(DefenseType.LIFE)
        assert len(life_builds) > 0
        for arch in life_builds:
            assert DefenseType.LIFE in arch.defense_types

    def test_get_league_starters(self, db):
        """get_league_starters returns league starter builds."""
        starters = db.get_league_starters()
        assert len(starters) > 0
        for arch in starters:
            assert arch.league_starter is True

    def test_get_ssf_viable(self, db):
        """get_ssf_viable returns SSF viable builds."""
        ssf = db.get_ssf_viable()
        assert len(ssf) > 0
        for arch in ssf:
            assert arch.ssf_viable is True

    def test_get_by_budget(self, db):
        """get_by_budget filters by budget tier."""
        budget = db.get_by_budget(1)
        assert len(budget) > 0
        for arch in budget:
            assert arch.budget_tier <= 1

        mid = db.get_by_budget(2)
        assert len(mid) >= len(budget)

    def test_get_by_tag(self, db):
        """get_by_tag filters by tag."""
        tanky = db.get_by_tag("tanky")
        assert len(tanky) > 0
        for arch in tanky:
            assert "tanky" in arch.tags

    def test_get_popular(self, db):
        """get_popular filters by popularity."""
        popular = db.get_popular(min_popularity=0.04)
        assert len(popular) > 0
        for arch in popular:
            assert arch.popularity >= 0.04

    def test_search_by_name(self, db):
        """search finds archetypes by name."""
        results = db.search("juggernaut")
        assert len(results) > 0
        # Should find RF Jugg and Boneshatter Jugg
        names = [r.name for r in results]
        assert any("Juggernaut" in name for name in names)

    def test_search_by_tag(self, db):
        """search finds archetypes by tag."""
        results = db.search("minion")
        assert len(results) > 0
        # Should find minion builds
        for r in results:
            assert "minion" in r.tags or "minion" in r.description.lower()

    def test_search_case_insensitive(self, db):
        """search is case insensitive."""
        lower = db.search("rf")
        upper = db.search("RF")
        assert len(lower) == len(upper)


class TestGetArchetypeDatabase:
    """Tests for get_archetype_database singleton."""

    def test_returns_database(self):
        """get_archetype_database returns an ArchetypeDatabase."""
        db = get_archetype_database()
        assert isinstance(db, ArchetypeDatabase)

    def test_singleton_behavior(self):
        """get_archetype_database returns same instance."""
        db1 = get_archetype_database()
        db2 = get_archetype_database()
        assert db1 is db2


class TestArchetypeDataQuality:
    """Tests for archetype data quality."""

    @pytest.fixture
    def db(self):
        """Get the archetype database."""
        return ArchetypeDatabase()

    def test_all_archetypes_have_key_stats(self, db):
        """All archetypes have at least one key stat."""
        for arch in db.get_all():
            assert len(arch.key_stats) > 0, f"{arch.name} has no key stats"

    def test_all_archetypes_have_damage_or_defense(self, db):
        """All archetypes have damage or defense types."""
        for arch in db.get_all():
            has_damage = len(arch.damage_types) > 0
            has_defense = len(arch.defense_types) > 0
            # Support builds might not have damage types
            if arch.category != BuildCategory.AURA_SUPPORT:
                assert has_damage, f"{arch.name} has no damage types"
            assert has_defense, f"{arch.name} has no defense types"

    def test_popularity_in_valid_range(self, db):
        """Popularity values are in valid range."""
        for arch in db.get_all():
            assert 0.0 <= arch.popularity <= 1.0, f"{arch.name} has invalid popularity"

    def test_budget_tier_valid(self, db):
        """Budget tiers are valid (1-3)."""
        for arch in db.get_all():
            assert arch.budget_tier in [1, 2, 3], f"{arch.name} has invalid budget tier"

    def test_rf_juggernaut_stats(self, db):
        """RF Juggernaut has expected stats."""
        rf = db.get_by_id("rf_juggernaut")
        assert rf is not None
        # RF needs life, fire res, regen
        stat_names = [s.stat_name for s in rf.key_stats]
        assert "maximum_life" in stat_names
        assert "life_regeneration_rate" in stat_names
        assert "fire_resistance" in stat_names

    def test_minion_builds_have_minion_stats(self, db):
        """Minion builds have minion damage stats."""
        minions = db.get_by_category(BuildCategory.MINION)
        for arch in minions:
            stat_names = [s.stat_name for s in arch.key_stats]
            assert "minion_damage" in stat_names, f"{arch.name} missing minion_damage"
