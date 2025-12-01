"""
Tests for Meta Analyzer Module.

Tests the meta affix analysis functionality including:
- AffixPopularity dataclass
- MetaAnalyzer methods for analyzing builds
- Dynamic weight generation
- Cache save/load functionality
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
import tempfile

from core.meta_analyzer import (
    AffixPopularity,
    MetaAnalyzer,
)


class TestAffixPopularity:
    """Tests for AffixPopularity dataclass."""

    def test_basic_creation(self):
        """Test creating a basic AffixPopularity."""
        pop = AffixPopularity(
            affix_pattern="+# to maximum Life",
            affix_type="life",
            appearance_count=50,
            total_builds=100,
        )
        assert pop.affix_pattern == "+# to maximum Life"
        assert pop.affix_type == "life"
        assert pop.appearance_count == 50
        assert pop.total_builds == 100

    def test_popularity_percent(self):
        """Test popularity percentage calculation."""
        pop = AffixPopularity(
            affix_pattern="+# to maximum Life",
            affix_type="life",
            appearance_count=75,
            total_builds=100,
        )
        assert pop.popularity_percent == 75.0

    def test_popularity_percent_zero_builds(self):
        """Test popularity percentage with zero builds."""
        pop = AffixPopularity(
            affix_pattern="+# to maximum Life",
            affix_type="life",
            appearance_count=10,
            total_builds=0,
        )
        assert pop.popularity_percent == 0.0

    def test_optional_fields(self):
        """Test optional fields have correct defaults."""
        pop = AffixPopularity(
            affix_pattern="+#% to Fire Resistance",
            affix_type="resistances",
        )
        assert pop.appearance_count == 0
        assert pop.total_builds == 0
        assert pop.min_value is None
        assert pop.max_value is None
        assert pop.avg_value is None
        assert pop.popular_with == []

    def test_with_value_ranges(self):
        """Test with value range data."""
        pop = AffixPopularity(
            affix_pattern="+# to maximum Life",
            affix_type="life",
            appearance_count=100,
            total_builds=200,
            min_value=80.0,
            max_value=130.0,
            avg_value=105.0,
        )
        assert pop.min_value == 80.0
        assert pop.max_value == 130.0
        assert pop.avg_value == 105.0

    def test_with_popular_classes(self):
        """Test with popular class data."""
        pop = AffixPopularity(
            affix_pattern="#% increased Movement Speed",
            affix_type="movement_speed",
            popular_with=["Raider", "Pathfinder", "Deadeye"],
        )
        assert len(pop.popular_with) == 3
        assert "Raider" in pop.popular_with


class TestMetaAnalyzer:
    """Tests for MetaAnalyzer class."""

    def test_initialization_default_cache(self):
        """Test default initialization."""
        analyzer = MetaAnalyzer()
        assert analyzer.cache_file == Path("data/meta_affixes.json")
        assert analyzer.builds_analyzed == 0
        assert analyzer.last_analysis is None
        assert len(analyzer.affix_patterns) > 0

    def test_initialization_custom_cache(self):
        """Test initialization with custom cache file."""
        custom_path = Path("custom/cache.json")
        analyzer = MetaAnalyzer(cache_file=custom_path)
        assert analyzer.cache_file == custom_path

    def test_identify_affix_type_life(self):
        """Test identifying life affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Maximum Life") == "life"
        assert analyzer._identify_affix_type("life regeneration") == "life"
        assert analyzer._identify_affix_type("+99 to Life") == "life"

    def test_identify_affix_type_movement(self):
        """Test identifying movement speed affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Movement Speed") == "movement_speed"
        assert analyzer._identify_affix_type("increased move speed") == "movement_speed"

    def test_identify_affix_type_attack_speed(self):
        """Test identifying attack speed affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Attack Speed") == "attack_speed"
        assert analyzer._identify_affix_type("increased attack speed") == "attack_speed"

    def test_identify_affix_type_cast_speed(self):
        """Test identifying cast speed affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Cast Speed") == "cast_speed"
        assert analyzer._identify_affix_type("faster cast speed") == "cast_speed"

    def test_identify_affix_type_spell_suppression(self):
        """Test identifying spell suppression affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Spell Suppression") == "spell_suppression"
        assert analyzer._identify_affix_type("suppress spell damage") == "spell_suppression"

    def test_identify_affix_type_energy_shield(self):
        """Test identifying energy shield affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Energy Shield") == "energy_shield"
        # Note: "es" alone matches but "maximum ES" doesn't match the specific pattern
        assert analyzer._identify_affix_type("es") == "energy_shield"

    def test_identify_affix_type_critical(self):
        """Test identifying critical strike affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Critical Strike Multiplier") == "critical_strike_multiplier"
        assert analyzer._identify_affix_type("critical mult") == "critical_strike_multiplier"

    def test_identify_affix_type_resistances(self):
        """Test identifying resistance affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Fire Resistance") == "resistances"
        assert analyzer._identify_affix_type("Cold Resistance") == "resistances"
        assert analyzer._identify_affix_type("Lightning Resistance") == "resistances"

    def test_identify_affix_type_chaos_resistance(self):
        """Test identifying chaos resistance affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Chaos Resistance") == "chaos_resistance"

    def test_identify_affix_type_attributes(self):
        """Test identifying attribute affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Strength") == "attributes"
        assert analyzer._identify_affix_type("Dexterity") == "attributes"
        assert analyzer._identify_affix_type("Intelligence") == "attributes"

    def test_identify_affix_type_mana(self):
        """Test identifying mana affixes."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("Maximum Mana") == "mana"

    def test_identify_affix_type_unknown(self):
        """Test unknown affix types return None."""
        analyzer = MetaAnalyzer()
        assert analyzer._identify_affix_type("random gibberish") is None
        assert analyzer._identify_affix_type("") is None

    def test_analyze_builds_empty(self):
        """Test analyzing empty build list."""
        analyzer = MetaAnalyzer()
        result = analyzer.analyze_builds([], league="Test")
        assert analyzer.builds_analyzed == 0
        assert len(result) == 0

    def test_analyze_builds_with_mocks(self):
        """Test analyzing builds with mock build objects."""
        analyzer = MetaAnalyzer(cache_file=None)  # Disable caching

        # Create mock builds
        mock_build1 = Mock()
        mock_build1.desired_affixes = ["Movement Speed", "Life"]
        mock_build1.build_name = "Speed Build"
        mock_build1.required_life = 5000
        mock_build1.required_es = 0
        mock_build1.required_resistances = None

        mock_build2 = Mock()
        mock_build2.desired_affixes = ["Life", "Fire Resistance"]
        mock_build2.build_name = "Tank Build"
        mock_build2.required_life = 7000
        mock_build2.required_es = 0
        mock_build2.required_resistances = {"fire": 75}

        builds = [mock_build1, mock_build2]

        with patch.object(analyzer, '_save_cache'):
            result = analyzer.analyze_builds(builds, league="Test")

        assert analyzer.builds_analyzed == 2
        assert "life" in result
        assert "movement_speed" in result
        assert result["life"].appearance_count >= 2

    def test_analyze_builds_with_es(self):
        """Test analyzing builds with energy shield requirements."""
        analyzer = MetaAnalyzer(cache_file=None)

        mock_build = Mock()
        mock_build.desired_affixes = ["Energy Shield"]
        mock_build.build_name = "ES Build"
        mock_build.required_life = 0
        mock_build.required_es = 3000
        mock_build.required_resistances = None

        with patch.object(analyzer, '_save_cache'):
            result = analyzer.analyze_builds([mock_build], league="Test")

        assert "energy_shield" in result

    def test_analyze_builds_with_chaos_resistance(self):
        """Test analyzing builds with chaos resistance requirements."""
        analyzer = MetaAnalyzer(cache_file=None)

        mock_build = Mock()
        mock_build.desired_affixes = []
        mock_build.build_name = "Chaos Build"
        mock_build.required_life = 0
        mock_build.required_es = 0
        mock_build.required_resistances = {"chaos": 75}

        with patch.object(analyzer, '_save_cache'):
            result = analyzer.analyze_builds([mock_build], league="Test")

        assert "chaos_resistance" in result

    def test_get_top_affixes_empty(self):
        """Test getting top affixes from empty analyzer."""
        analyzer = MetaAnalyzer()
        result = analyzer.get_top_affixes(10)
        assert result == []

    def test_get_top_affixes(self):
        """Test getting top affixes after analysis."""
        analyzer = MetaAnalyzer(cache_file=None)

        # Manually populate affix_popularity
        analyzer.affix_popularity = {
            "life": AffixPopularity("+# to maximum Life", "life", 100, 100),
            "resistances": AffixPopularity("+#% Resistance", "resistances", 80, 100),
            "movement_speed": AffixPopularity("#% Movement", "movement_speed", 60, 100),
        }

        top = analyzer.get_top_affixes(2)
        assert len(top) == 2
        assert top[0][0] == "life"
        assert top[1][0] == "resistances"

    def test_generate_dynamic_weights_empty(self):
        """Test generating weights with no data."""
        analyzer = MetaAnalyzer()
        result = analyzer.generate_dynamic_weights()
        assert result == {}

    def test_generate_dynamic_weights(self):
        """Test generating dynamic weights."""
        analyzer = MetaAnalyzer()
        analyzer.affix_popularity = {
            "life": AffixPopularity("+# to maximum Life", "life", 100, 100),  # 100% popularity
            "resistances": AffixPopularity("+#% Resistance", "resistances", 50, 100),  # 50% popularity
        }

        weights = analyzer.generate_dynamic_weights(base_weight=5.0, popularity_multiplier=0.1)

        # life: 5.0 + (100 * 0.1) = 15.0
        # resistances: 5.0 + (50 * 0.1) = 10.0
        assert weights["life"] == 15.0
        assert weights["resistances"] == 10.0

    def test_save_cache(self):
        """Test saving cache to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            analyzer = MetaAnalyzer(cache_file=cache_file)

            analyzer.builds_analyzed = 10
            analyzer.last_analysis = datetime.now()
            analyzer.affix_popularity = {
                "life": AffixPopularity(
                    affix_pattern="+# to maximum Life",
                    affix_type="life",
                    appearance_count=8,
                    total_builds=10,
                    min_value=80.0,
                    max_value=120.0,
                    avg_value=100.0,
                    popular_with=["Juggernaut"],
                )
            }

            analyzer._save_cache("TestLeague")

            assert cache_file.exists()

            with open(cache_file, 'r') as f:
                data = json.load(f)

            assert data["league"] == "TestLeague"
            assert data["builds_analyzed"] == 10
            assert "life" in data["affixes"]

    def test_load_cache_no_file(self):
        """Test loading cache when file doesn't exist."""
        analyzer = MetaAnalyzer(cache_file=Path("nonexistent/path.json"))
        result = analyzer.load_cache()
        assert result is False

    def test_load_cache_success(self):
        """Test loading cache successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"

            # Write test cache
            cache_data = {
                "league": "TestLeague",
                "builds_analyzed": 5,
                "last_analysis": datetime.now().isoformat(),
                "affixes": {
                    "life": {
                        "pattern": "+# to maximum Life",
                        "appearance_count": 4,
                        "total_builds": 5,
                        "popularity_percent": 80.0,
                        "min_value": 80.0,
                        "max_value": 100.0,
                        "avg_value": 90.0,
                        "popular_with": ["Marauder"],
                    }
                }
            }

            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)

            analyzer = MetaAnalyzer(cache_file=cache_file)
            result = analyzer.load_cache()

            assert result is True
            assert analyzer.builds_analyzed == 5
            assert "life" in analyzer.affix_popularity
            assert analyzer.affix_popularity["life"].appearance_count == 4

    def test_load_cache_invalid_json(self):
        """Test loading cache with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"

            with open(cache_file, 'w') as f:
                f.write("invalid json {{{")

            analyzer = MetaAnalyzer(cache_file=cache_file)
            result = analyzer.load_cache()
            assert result is False

    def test_load_cache_nonexistent_path(self):
        """Test loading cache with nonexistent file path."""
        # Note: cache_file=None falls back to default path, so use explicit nonexistent path
        analyzer = MetaAnalyzer(cache_file=Path("/nonexistent/path/that/does/not/exist.json"))
        result = analyzer.load_cache()
        assert result is False

    def test_print_summary(self, capsys):
        """Test print_summary output."""
        analyzer = MetaAnalyzer()
        analyzer.builds_analyzed = 10
        analyzer.last_analysis = datetime(2024, 1, 1, 12, 0, 0)
        analyzer.affix_popularity = {
            "life": AffixPopularity(
                affix_pattern="+# to maximum Life",
                affix_type="life",
                appearance_count=8,
                total_builds=10,
                avg_value=100.0,
                min_value=80.0,
                max_value=120.0,
                popular_with=["Juggernaut", "Berserker"],
            ),
        }

        analyzer.print_summary()

        captured = capsys.readouterr()
        assert "META AFFIX ANALYSIS" in captured.out
        assert "Builds Analyzed: 10" in captured.out
        assert "life" in captured.out

    def test_affix_patterns_defined(self):
        """Test that common affix patterns are defined."""
        analyzer = MetaAnalyzer()
        assert "life" in analyzer.affix_patterns
        assert "resistances" in analyzer.affix_patterns
        assert "movement_speed" in analyzer.affix_patterns
        assert "energy_shield" in analyzer.affix_patterns
        assert "critical_strike_multiplier" in analyzer.affix_patterns


class TestMetaAnalyzerIntegration:
    """Integration tests for MetaAnalyzer with mocked builds."""

    def test_full_analysis_workflow(self):
        """Test complete analysis workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "meta.json"
            analyzer = MetaAnalyzer(cache_file=cache_file)

            # Create mock builds
            builds = []
            for i in range(5):
                build = Mock()
                build.build_name = f"Build {i}"
                build.desired_affixes = ["Life", "Movement Speed"]
                build.required_life = 4000 + (i * 500)
                build.required_es = 0
                build.required_resistances = {"fire": 75}
                builds.append(build)

            # Analyze
            result = analyzer.analyze_builds(builds, league="Integration")

            # Verify results
            assert analyzer.builds_analyzed == 5
            assert "life" in result
            assert "movement_speed" in result
            assert "resistances" in result

            # Check values were tracked
            assert result["life"].min_value is not None
            assert result["life"].max_value is not None

            # Generate weights
            weights = analyzer.generate_dynamic_weights()
            assert len(weights) > 0

            # Check cache was saved
            assert cache_file.exists()

            # Create new analyzer and load cache
            analyzer2 = MetaAnalyzer(cache_file=cache_file)
            loaded = analyzer2.load_cache()
            assert loaded is True
            assert analyzer2.builds_analyzed == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
