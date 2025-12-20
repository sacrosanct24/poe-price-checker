"""Tests for core/meta_analyzer.py."""
from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock



class TestAffixPopularity:
    """Tests for AffixPopularity dataclass."""

    def test_creation(self):
        """Test creating AffixPopularity."""
        from core.meta_analyzer import AffixPopularity

        pop = AffixPopularity(
            affix_pattern="+# to maximum Life",
            affix_type="life",
            appearance_count=50,
            total_builds=100,
            min_value=70.0,
            max_value=120.0,
            avg_value=95.0,
            popular_with=["Juggernaut", "Marauder"],
        )

        assert pop.affix_pattern == "+# to maximum Life"
        assert pop.affix_type == "life"
        assert pop.appearance_count == 50
        assert pop.total_builds == 100
        assert pop.min_value == 70.0
        assert pop.max_value == 120.0
        assert pop.avg_value == 95.0
        assert pop.popular_with == ["Juggernaut", "Marauder"]

    def test_defaults(self):
        """Test default values."""
        from core.meta_analyzer import AffixPopularity

        pop = AffixPopularity(
            affix_pattern="+#% Fire Resistance",
            affix_type="resistances",
        )

        assert pop.appearance_count == 0
        assert pop.total_builds == 0
        assert pop.min_value is None
        assert pop.max_value is None
        assert pop.avg_value is None
        assert pop.popular_with == []

    def test_popularity_percent(self):
        """Test popularity_percent calculation."""
        from core.meta_analyzer import AffixPopularity

        pop = AffixPopularity(
            affix_pattern="test",
            affix_type="test",
            appearance_count=75,
            total_builds=100,
        )

        assert pop.popularity_percent == 75.0

    def test_popularity_percent_zero_builds(self):
        """Test popularity_percent with zero total builds."""
        from core.meta_analyzer import AffixPopularity

        pop = AffixPopularity(
            affix_pattern="test",
            affix_type="test",
            appearance_count=0,
            total_builds=0,
        )

        assert pop.popularity_percent == 0.0

    def test_popularity_percent_partial(self):
        """Test popularity_percent with partial values."""
        from core.meta_analyzer import AffixPopularity

        pop = AffixPopularity(
            affix_pattern="test",
            affix_type="test",
            appearance_count=33,
            total_builds=100,
        )

        assert pop.popularity_percent == 33.0


class TestMetaAnalyzerInit:
    """Tests for MetaAnalyzer initialization."""

    def test_init_defaults(self):
        """Test default initialization."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer.cache_file == Path("data/meta_affixes.json")
        assert analyzer.builds_analyzed == 0
        assert analyzer.last_analysis is None
        assert analyzer.affix_popularity == {}

    def test_init_custom_cache(self):
        """Test initialization with custom cache file."""
        from core.meta_analyzer import MetaAnalyzer

        custom_path = Path("/tmp/custom_cache.json")
        analyzer = MetaAnalyzer(cache_file=custom_path)

        assert analyzer.cache_file == custom_path

    def test_affix_patterns_defined(self):
        """Test that affix patterns are properly defined."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        # Check key patterns exist
        assert 'life' in analyzer.affix_patterns
        assert 'resistances' in analyzer.affix_patterns
        assert 'movement_speed' in analyzer.affix_patterns
        assert 'energy_shield' in analyzer.affix_patterns
        assert 'spell_suppression' in analyzer.affix_patterns


class TestMetaAnalyzerIdentifyAffixType:
    """Tests for _identify_affix_type method."""

    def test_identify_life(self):
        """Test identifying life affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("Maximum Life") == "life"
        assert analyzer._identify_affix_type("+100 to Life") == "life"
        assert analyzer._identify_affix_type("life regeneration") == "life"

    def test_identify_movement_speed(self):
        """Test identifying movement speed affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("increased Movement Speed") == "movement_speed"
        assert analyzer._identify_affix_type("move faster") == "movement_speed"

    def test_identify_attack_speed(self):
        """Test identifying attack speed affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("increased Attack Speed") == "attack_speed"

    def test_identify_cast_speed(self):
        """Test identifying cast speed affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("increased Cast Speed") == "cast_speed"

    def test_identify_spell_suppression(self):
        """Test identifying spell suppression affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("Suppress Spell Damage") == "spell_suppression"
        assert analyzer._identify_affix_type("spell suppression chance") == "spell_suppression"

    def test_identify_energy_shield(self):
        """Test identifying energy shield affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("maximum Energy Shield") == "energy_shield"
        assert analyzer._identify_affix_type("ES") == "energy_shield"

    def test_identify_crit_multi(self):
        """Test identifying critical strike multiplier."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("Critical Strike Multiplier") == "critical_strike_multiplier"

    def test_identify_resistances(self):
        """Test identifying elemental resistances."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("Fire Resistance") == "resistances"
        assert analyzer._identify_affix_type("Cold Resistance") == "resistances"
        assert analyzer._identify_affix_type("Lightning Resistance") == "resistances"

    def test_identify_chaos_resistance(self):
        """Test identifying chaos resistance."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("Chaos Resistance") == "chaos_resistance"

    def test_identify_attributes(self):
        """Test identifying attribute affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("to Strength") == "attributes"
        assert analyzer._identify_affix_type("to Dexterity") == "attributes"
        assert analyzer._identify_affix_type("to Intelligence") == "attributes"

    def test_identify_mana(self):
        """Test identifying mana affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("maximum Mana") == "mana"

    def test_identify_unknown(self):
        """Test identifying unknown affix returns None."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()

        assert analyzer._identify_affix_type("random unknown affix") is None
        assert analyzer._identify_affix_type("bleed chance") is None


class TestMetaAnalyzerAnalyzeBuilds:
    """Tests for analyze_builds method."""

    def test_analyze_empty_builds(self):
        """Test analyzing empty build list."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)
        result = analyzer.analyze_builds([], league="Test")

        assert result == {}
        assert analyzer.builds_analyzed == 0

    def test_analyze_builds_with_life(self):
        """Test analyzing builds with life requirements."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        # Create mock builds
        mock_build1 = MagicMock()
        mock_build1.desired_affixes = []
        mock_build1.required_life = 5000
        mock_build1.required_es = 0
        mock_build1.required_resistances = {}
        mock_build1.build_name = "Test Build 1"

        mock_build2 = MagicMock()
        mock_build2.desired_affixes = []
        mock_build2.required_life = 6000
        mock_build2.required_es = 0
        mock_build2.required_resistances = {}
        mock_build2.build_name = "Test Build 2"

        result = analyzer.analyze_builds([mock_build1, mock_build2])

        assert 'life' in result
        assert result['life'].appearance_count == 2
        assert result['life'].total_builds == 2
        assert result['life'].popularity_percent == 100.0
        assert result['life'].min_value == 5000
        assert result['life'].max_value == 6000
        assert result['life'].avg_value == 5500.0

    def test_analyze_builds_with_es(self):
        """Test analyzing builds with ES requirements."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        mock_build = MagicMock()
        mock_build.desired_affixes = []
        mock_build.required_life = 0
        mock_build.required_es = 3000
        mock_build.required_resistances = {}
        mock_build.build_name = "ES Build"

        result = analyzer.analyze_builds([mock_build])

        assert 'energy_shield' in result
        assert result['energy_shield'].appearance_count == 1

    def test_analyze_builds_with_resistances(self):
        """Test analyzing builds with resistance requirements."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        mock_build = MagicMock()
        mock_build.desired_affixes = []
        mock_build.required_life = 0
        mock_build.required_es = 0
        mock_build.required_resistances = {"fire": 75, "chaos": 60}
        mock_build.build_name = "Res Build"

        result = analyzer.analyze_builds([mock_build])

        assert 'resistances' in result
        assert 'chaos_resistance' in result

    def test_analyze_builds_with_desired_affixes(self):
        """Test analyzing builds with desired affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        mock_build = MagicMock()
        mock_build.desired_affixes = ["Movement Speed", "Attack Speed"]
        mock_build.required_life = 0
        mock_build.required_es = 0
        mock_build.required_resistances = {}
        mock_build.build_name = "Speed Build"

        result = analyzer.analyze_builds([mock_build])

        assert 'movement_speed' in result
        assert 'attack_speed' in result

    def test_analyze_sets_last_analysis(self):
        """Test that analysis sets last_analysis timestamp."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        before = datetime.now()
        analyzer.analyze_builds([])
        after = datetime.now()

        assert analyzer.last_analysis is not None
        assert before <= analyzer.last_analysis <= after


class TestMetaAnalyzerGetTopAffixes:
    """Tests for get_top_affixes method."""

    def test_get_top_affixes_empty(self):
        """Test get_top_affixes with no data."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()
        result = analyzer.get_top_affixes()

        assert result == []

    def test_get_top_affixes_sorted(self):
        """Test get_top_affixes returns sorted results."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        analyzer = MetaAnalyzer()
        analyzer.affix_popularity = {
            'life': AffixPopularity("life", "life", appearance_count=100, total_builds=100),
            'resistances': AffixPopularity("res", "resistances", appearance_count=80, total_builds=100),
            'movement': AffixPopularity("ms", "movement", appearance_count=50, total_builds=100),
        }

        result = analyzer.get_top_affixes(limit=10)

        assert len(result) == 3
        assert result[0][0] == 'life'  # Most popular
        assert result[1][0] == 'resistances'
        assert result[2][0] == 'movement'

    def test_get_top_affixes_limit(self):
        """Test get_top_affixes respects limit."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        analyzer = MetaAnalyzer()
        analyzer.affix_popularity = {
            'a': AffixPopularity("a", "a", appearance_count=100, total_builds=100),
            'b': AffixPopularity("b", "b", appearance_count=90, total_builds=100),
            'c': AffixPopularity("c", "c", appearance_count=80, total_builds=100),
            'd': AffixPopularity("d", "d", appearance_count=70, total_builds=100),
        }

        result = analyzer.get_top_affixes(limit=2)

        assert len(result) == 2
        assert result[0][0] == 'a'
        assert result[1][0] == 'b'


class TestMetaAnalyzerGenerateDynamicWeights:
    """Tests for generate_dynamic_weights method."""

    def test_generate_weights_empty(self):
        """Test generating weights with no data."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()
        result = analyzer.generate_dynamic_weights()

        assert result == {}

    def test_generate_weights_basic(self):
        """Test generating weights with data."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        analyzer = MetaAnalyzer()
        analyzer.affix_popularity = {
            'life': AffixPopularity("life", "life", appearance_count=100, total_builds=100),
            'mana': AffixPopularity("mana", "mana", appearance_count=50, total_builds=100),
        }

        result = analyzer.generate_dynamic_weights(base_weight=5.0, popularity_multiplier=0.1)

        # life: 100% popularity -> 5.0 + (100 * 0.1) = 15.0
        assert result['life'] == 15.0
        # mana: 50% popularity -> 5.0 + (50 * 0.1) = 10.0
        assert result['mana'] == 10.0

    def test_generate_weights_custom_params(self):
        """Test generating weights with custom parameters."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        analyzer = MetaAnalyzer()
        analyzer.affix_popularity = {
            'life': AffixPopularity("life", "life", appearance_count=50, total_builds=100),
        }

        result = analyzer.generate_dynamic_weights(base_weight=10.0, popularity_multiplier=0.2)

        # 50% popularity -> 10.0 + (50 * 0.2) = 20.0
        assert result['life'] == 20.0


class TestMetaAnalyzerCache:
    """Tests for cache save/load functionality."""

    def test_save_cache(self):
        """Test saving cache to file."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "meta_cache.json"
            analyzer = MetaAnalyzer(cache_file=cache_file)

            analyzer.affix_popularity = {
                'life': AffixPopularity(
                    affix_pattern="+# to Life",
                    affix_type="life",
                    appearance_count=75,
                    total_builds=100,
                    min_value=50.0,
                    max_value=100.0,
                    avg_value=75.0,
                    popular_with=["Jugg"],
                )
            }
            analyzer.builds_analyzed = 100
            analyzer.last_analysis = datetime.now()

            analyzer._save_cache("TestLeague")

            assert cache_file.exists()

            # Verify content
            with open(cache_file) as f:
                data = json.load(f)

            assert data['league'] == "TestLeague"
            assert data['builds_analyzed'] == 100
            assert 'life' in data['affixes']
            assert data['affixes']['life']['appearance_count'] == 75

    def test_save_cache_no_file(self):
        """Test save_cache with no cache file."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        # Should not raise
        analyzer._save_cache("Test")

    def test_load_cache_success(self):
        """Test loading cache from file."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "meta_cache.json"

            # Create cache file
            cache_data = {
                'league': 'TestLeague',
                'builds_analyzed': 50,
                'last_analysis': '2024-01-15T10:30:00',
                'affixes': {
                    'life': {
                        'pattern': '+# Life',
                        'appearance_count': 40,
                        'total_builds': 50,
                        'min_value': 60.0,
                        'max_value': 90.0,
                        'avg_value': 75.0,
                        'popular_with': ['Marauder'],
                    }
                }
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)

            analyzer = MetaAnalyzer(cache_file=cache_file)
            result = analyzer.load_cache()

            assert result is True
            assert analyzer.builds_analyzed == 50
            assert analyzer.last_analysis is not None
            assert 'life' in analyzer.affix_popularity
            assert analyzer.affix_popularity['life'].appearance_count == 40

    def test_load_cache_no_file(self):
        """Test loading cache when file doesn't exist."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=Path("/nonexistent/cache.json"))
        result = analyzer.load_cache()

        assert result is False

    def test_load_cache_none_file(self):
        """Test loading cache with no cache file configured."""
        from core.meta_analyzer import MetaAnalyzer

        # Create analyzer with explicit None cache_file
        analyzer = MetaAnalyzer()
        analyzer.cache_file = None  # Explicitly set to None after init
        result = analyzer.load_cache()

        assert result is False

    def test_load_cache_invalid_json(self):
        """Test loading cache with invalid JSON."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "invalid.json"
            cache_file.write_text("{ invalid json }")

            analyzer = MetaAnalyzer(cache_file=cache_file)
            result = analyzer.load_cache()

            assert result is False

    def test_load_cache_without_last_analysis(self):
        """Test loading cache without last_analysis field."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "meta_cache.json"

            cache_data = {
                'league': 'Test',
                'builds_analyzed': 10,
                'last_analysis': None,
                'affixes': {}
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)

            analyzer = MetaAnalyzer(cache_file=cache_file)
            result = analyzer.load_cache()

            assert result is True
            assert analyzer.last_analysis is None


class TestMetaAnalyzerPrintSummary:
    """Tests for print_summary method."""

    def test_print_summary_empty(self, capsys):
        """Test print_summary with no data."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()
        analyzer.print_summary()

        captured = capsys.readouterr()
        assert "META AFFIX ANALYSIS" in captured.out
        assert "Builds Analyzed: 0" in captured.out

    def test_print_summary_with_data(self, capsys):
        """Test print_summary with data."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        analyzer = MetaAnalyzer()
        analyzer.builds_analyzed = 100
        analyzer.last_analysis = datetime(2024, 1, 15, 10, 30)
        analyzer.affix_popularity = {
            'life': AffixPopularity(
                affix_pattern="+# Life",
                affix_type="life",
                appearance_count=80,
                total_builds=100,
                avg_value=95.0,
                min_value=70.0,
                max_value=120.0,
                popular_with=["Juggernaut", "Marauder", "Berserker"],
            )
        }

        analyzer.print_summary()

        captured = capsys.readouterr()
        assert "META AFFIX ANALYSIS" in captured.out
        assert "Builds Analyzed: 100" in captured.out
        assert "80.0%" in captured.out
        assert "life" in captured.out
        assert "Avg Value: 95.0" in captured.out
        assert "Juggernaut" in captured.out


class TestMetaAnalyzerIntegration:
    """Integration tests for MetaAnalyzer."""

    def test_full_workflow(self):
        """Test complete analyze -> cache -> load workflow."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "meta_cache.json"

            # Create and analyze
            analyzer1 = MetaAnalyzer(cache_file=cache_file)

            mock_build = MagicMock()
            mock_build.desired_affixes = ["Life", "Movement Speed"]
            mock_build.required_life = 5000
            mock_build.required_es = 0
            mock_build.required_resistances = {"fire": 75}
            mock_build.build_name = "Test Build"

            analyzer1.analyze_builds([mock_build], league="Test")

            # Create new analyzer and load cache
            analyzer2 = MetaAnalyzer(cache_file=cache_file)
            loaded = analyzer2.load_cache()

            assert loaded is True
            assert analyzer2.builds_analyzed == 1
            assert 'life' in analyzer2.affix_popularity
            assert 'movement_speed' in analyzer2.affix_popularity

    def test_analyze_multiple_builds(self):
        """Test analyzing multiple builds with varied data."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        builds = []
        for i in range(10):
            mock_build = MagicMock()
            # Use distinct affix names that don't overlap in pattern matching
            mock_build.desired_affixes = ["Movement Speed"] if i % 2 == 0 else ["Cast Speed"]
            mock_build.required_life = 5000 if i % 2 == 0 else 0
            mock_build.required_es = 0 if i % 2 == 0 else 3000
            mock_build.required_resistances = {}
            mock_build.build_name = f"Build {i}"
            builds.append(mock_build)

        result = analyzer.analyze_builds(builds)

        assert analyzer.builds_analyzed == 10
        # movement_speed should appear in 5 builds (even indices)
        assert 'movement_speed' in result
        assert result['movement_speed'].appearance_count == 5
        assert result['movement_speed'].popularity_percent == 50.0


# =============================================================================
# Meta Builds Knowledge Tests
# =============================================================================


class TestLoadMetaBuildsKnowledge:
    """Tests for load_meta_builds_knowledge method."""

    def test_load_missing_file(self):
        """Test loading when file doesn't exist."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()
        result = analyzer.load_meta_builds_knowledge(
            game_version="poe1",
            knowledge_dir=Path("/nonexistent/path")
        )

        assert result == {}

    def test_load_valid_knowledge_file(self):
        """Test loading valid knowledge file."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            knowledge_dir = Path(tmpdir)
            knowledge_file = knowledge_dir / "current_league.json"

            knowledge_data = {
                "league": "TestLeague",
                "affix_meta_weights": {
                    "life": {"base_weight": 5.0, "meta_multiplier": 1.2},
                    "movement_speed": {"base_weight": 4.0, "meta_multiplier": 1.5},
                },
                "builds": [
                    {
                        "name": "Lightning Strike",
                        "popularity_percent": 10,
                        "tier": "S",
                        "desired_affixes_global": [
                            {"name": "attack_speed", "weight": 8},
                        ]
                    }
                ]
            }

            with open(knowledge_file, 'w') as f:
                json.dump(knowledge_data, f)

            analyzer = MetaAnalyzer()
            result = analyzer.load_meta_builds_knowledge(
                game_version="poe1",
                knowledge_dir=knowledge_dir
            )

            assert 'life' in result
            assert result['life'] == 6.0  # 5.0 * 1.2
            assert result['movement_speed'] == 6.0  # 4.0 * 1.5
            assert 'attack_speed' in result

    def test_load_knowledge_with_tier_multipliers(self):
        """Test that tier multipliers affect affix weights."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            knowledge_dir = Path(tmpdir)
            knowledge_file = knowledge_dir / "current_league.json"

            knowledge_data = {
                "league": "TestLeague",
                "affix_meta_weights": {},
                "builds": [
                    {
                        "name": "S-Tier Build",
                        "popularity_percent": 20,
                        "tier": "S",  # 1.5 multiplier
                        "desired_affixes_global": [
                            {"name": "crit_chance", "weight": 10},
                        ]
                    },
                    {
                        "name": "D-Tier Build",
                        "popularity_percent": 5,
                        "tier": "D",  # 0.9 multiplier
                        "desired_affixes_global": [
                            {"name": "mana", "weight": 5},
                        ]
                    }
                ]
            }

            with open(knowledge_file, 'w') as f:
                json.dump(knowledge_data, f)

            analyzer = MetaAnalyzer()
            result = analyzer.load_meta_builds_knowledge(
                game_version="poe1",
                knowledge_dir=knowledge_dir
            )

            # S-tier with 20% popularity: 5.0 + 10 * (0.2 * 1.5) * 0.1 = 5.3
            assert 'crit_chance' in result
            # D-tier with 5% popularity: 5.0 + 5 * (0.05 * 0.9) * 0.1 ~ 5.02
            assert 'mana' in result

    def test_load_knowledge_invalid_json(self):
        """Test loading with invalid JSON file."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            knowledge_dir = Path(tmpdir)
            knowledge_file = knowledge_dir / "current_league.json"
            knowledge_file.write_text("{ invalid json")

            analyzer = MetaAnalyzer()
            result = analyzer.load_meta_builds_knowledge(
                game_version="poe1",
                knowledge_dir=knowledge_dir
            )

            assert result == {}

    def test_load_knowledge_stores_internal_data(self):
        """Test that loaded data is stored for later use."""
        from core.meta_analyzer import MetaAnalyzer

        with tempfile.TemporaryDirectory() as tmpdir:
            knowledge_dir = Path(tmpdir)
            knowledge_file = knowledge_dir / "current_league.json"

            knowledge_data = {
                "league": "TestLeague",
                "affix_meta_weights": {"life": {"base_weight": 5.0, "meta_multiplier": 1.0}},
                "builds": []
            }

            with open(knowledge_file, 'w') as f:
                json.dump(knowledge_data, f)

            analyzer = MetaAnalyzer()
            analyzer.load_meta_builds_knowledge(
                game_version="poe1",
                knowledge_dir=knowledge_dir
            )

            assert hasattr(analyzer, '_meta_knowledge_weights')
            assert hasattr(analyzer, '_meta_knowledge_data')


class TestGetMetaBuildMatches:
    """Tests for get_meta_build_matches method."""

    def test_no_knowledge_loaded(self):
        """Test when no knowledge data is loaded."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()
        result = analyzer.get_meta_build_matches(["life", "resistances"])

        assert result == []

    def test_find_matching_builds(self):
        """Test finding builds that match item affixes."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()
        # Manually set up internal data
        analyzer._meta_knowledge_data = {
            "builds": [
                {
                    "name": "RF Jugg",
                    "desired_affixes_global": [
                        {"name": "life"},
                        {"name": "fire_resistance"},
                        {"name": "life_regen"},
                    ]
                },
                {
                    "name": "LS Champion",
                    "desired_affixes_global": [
                        {"name": "attack_speed"},
                        {"name": "crit_chance"},
                        {"name": "life"},
                    ]
                },
                {
                    "name": "ES Build",
                    "desired_affixes_global": [
                        {"name": "energy_shield"},
                        {"name": "spell_damage"},
                    ]
                }
            ]
        }

        # Item has life and fire_res - should match RF Jugg
        result = analyzer.get_meta_build_matches(["life", "fire_resistance"])
        assert "RF Jugg" in result

        # Item has attack_speed and crit - should match LS Champion
        result2 = analyzer.get_meta_build_matches(["attack_speed", "crit_chance", "life"])
        assert "LS Champion" in result2

        # Item has only ES - only 1 match, needs 2
        result3 = analyzer.get_meta_build_matches(["energy_shield"])
        assert "ES Build" not in result3

    def test_overlap_threshold(self):
        """Test that at least 2 affixes must match."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer()
        analyzer._meta_knowledge_data = {
            "builds": [
                {
                    "name": "Test Build",
                    "desired_affixes_global": [
                        {"name": "life"},
                        {"name": "resistances"},
                        {"name": "movement_speed"},
                    ]
                }
            ]
        }

        # Only 1 match - not enough
        result = analyzer.get_meta_build_matches(["life"])
        assert result == []

        # 2 matches - enough
        result = analyzer.get_meta_build_matches(["life", "resistances"])
        assert "Test Build" in result


class TestSaveCacheErrorHandling:
    """Tests for _save_cache error handling."""

    def test_save_cache_exception(self):
        """Test save_cache handles exceptions gracefully."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=Path("/invalid/path/cache.json"))
        analyzer.affix_popularity = {}
        analyzer.builds_analyzed = 10
        analyzer.last_analysis = datetime.now()

        # Should not raise - error is logged
        analyzer._save_cache("Test")


class TestPrintSummaryBranches:
    """Tests for print_summary branch coverage."""

    def test_print_summary_without_avg_value(self, capsys):
        """Test print_summary when avg_value is None."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        analyzer = MetaAnalyzer()
        analyzer.builds_analyzed = 50
        analyzer.affix_popularity = {
            'life': AffixPopularity(
                affix_pattern="+# Life",
                affix_type="life",
                appearance_count=40,
                total_builds=50,
                avg_value=None,  # No avg value
                min_value=None,
                max_value=None,
                popular_with=[],  # No popular classes
            )
        }

        analyzer.print_summary()

        captured = capsys.readouterr()
        assert "life" in captured.out
        # Should NOT have "Avg Value" since it's None
        assert "Avg Value" not in captured.out
        # Should NOT have "Popular with" since list is empty
        assert "Popular with" not in captured.out

    def test_print_summary_with_popular_classes(self, capsys):
        """Test print_summary shows popular_with when present."""
        from core.meta_analyzer import MetaAnalyzer, AffixPopularity

        analyzer = MetaAnalyzer()
        analyzer.builds_analyzed = 50
        analyzer.affix_popularity = {
            'life': AffixPopularity(
                affix_pattern="+# Life",
                affix_type="life",
                appearance_count=40,
                total_builds=50,
                avg_value=95.0,
                min_value=70.0,
                max_value=120.0,
                popular_with=["Juggernaut", "Champion", "Berserker", "Slayer"],
            )
        }

        analyzer.print_summary()

        captured = capsys.readouterr()
        assert "Popular with:" in captured.out
        assert "Juggernaut" in captured.out


class TestAnalyzeBuildsBranchCoverage:
    """Tests for analyze_builds branch coverage."""

    def test_analyze_build_without_name(self):
        """Test analyzing build without build_name."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        mock_build = MagicMock()
        mock_build.desired_affixes = ["Movement Speed"]
        mock_build.required_life = 0
        mock_build.required_es = 0
        mock_build.required_resistances = {}
        mock_build.build_name = ""  # Empty build name

        result = analyzer.analyze_builds([mock_build])

        assert 'movement_speed' in result
        # Popular_with should be empty since no build name
        assert result['movement_speed'].popular_with == []

    def test_analyze_build_tracks_class_names(self):
        """Test that build names are tracked in popular_with."""
        from core.meta_analyzer import MetaAnalyzer

        analyzer = MetaAnalyzer(cache_file=None)

        mock_build1 = MagicMock()
        mock_build1.desired_affixes = ["Attack Speed"]
        mock_build1.required_life = 0
        mock_build1.required_es = 0
        mock_build1.required_resistances = {}
        mock_build1.build_name = "Lightning Strike"

        mock_build2 = MagicMock()
        mock_build2.desired_affixes = ["Attack Speed"]
        mock_build2.required_life = 0
        mock_build2.required_es = 0
        mock_build2.required_resistances = {}
        mock_build2.build_name = "Cyclone"

        result = analyzer.analyze_builds([mock_build1, mock_build2])

        assert 'attack_speed' in result
        # Should have both build names
        assert "Lightning Strike" in result['attack_speed'].popular_with
        assert "Cyclone" in result['attack_speed'].popular_with
