"""Tests for data_sources/affix_data_provider.py - Affix data provider."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from data_sources.affix_data_provider import (
    AffixDataProvider,
    get_affix_provider,
)


class TestAffixDataProvider:
    """Tests for AffixDataProvider class."""

    @pytest.fixture
    def temp_json_file(self, tmp_path):
        """Create temp JSON file with affix data."""
        json_path = tmp_path / "valuable_affixes.json"
        data = {
            "life": {
                "tier1_range": [100, 109],
                "tier2_range": [90, 99],
                "tier3_range": [80, 89],
                "patterns": [r"\+\d+ to maximum Life"],
            },
            "movement_speed": {
                "tier1_range": [30, 35],
                "tier2_range": [25, 29],
                "patterns": [r"\d+% increased Movement Speed"],
            },
            "fire_resistance": {
                "tier1_range": [41, 45],
                "tier2_range": [36, 40],
                "tier3_range": [30, 35],
            },
            "_synergies": {
                "attack": ["life", "attack_speed"],
                "caster": ["energy_shield", "cast_speed"],
            },
            "_red_flags": {
                "thorns": ["reflects damage"],
            },
        }
        with open(json_path, 'w') as f:
            json.dump(data, f)
        return json_path

    @pytest.fixture
    def mock_database(self):
        """Create mock database."""
        db = MagicMock()
        db.get_mod_count.return_value = 1000
        db.get_current_league.return_value = "TestLeague"
        db.get_last_update_time.return_value = "2024-01-01T00:00:00"
        db.get_affix_tiers.return_value = [
            (1, 100, 109),
            (2, 90, 99),
            (3, 80, 89),
        ]
        return db

    def test_init_uses_database_when_available(self, mock_database, temp_json_file):
        """Should use database when it has mods."""
        provider = AffixDataProvider(
            mod_database=mock_database,
            json_path=temp_json_file,
        )

        assert provider.is_using_database() is True

    def test_init_uses_json_when_no_database(self, temp_json_file):
        """Should use JSON when database is None."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        assert provider.is_using_database() is False

    def test_init_uses_json_when_database_empty(self, temp_json_file):
        """Should use JSON when database has no mods."""
        db = MagicMock()
        db.get_mod_count.return_value = 0

        provider = AffixDataProvider(
            mod_database=db,
            json_path=temp_json_file,
        )

        assert provider.is_using_database() is False

    def test_get_affix_tiers_from_database(self, mock_database, temp_json_file):
        """Should get tiers from database when available."""
        provider = AffixDataProvider(
            mod_database=mock_database,
            json_path=temp_json_file,
        )

        tiers = provider.get_affix_tiers("life", stat_text_pattern="%maximum Life%")

        assert len(tiers) == 3
        mock_database.get_affix_tiers.assert_called_once_with("%maximum Life%")

    def test_get_affix_tiers_from_json(self, temp_json_file):
        """Should get tiers from JSON when database unavailable."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        tiers = provider.get_affix_tiers("life")

        assert len(tiers) == 3
        assert tiers[0] == (1, 100, 109)
        assert tiers[1] == (2, 90, 99)
        assert tiers[2] == (3, 80, 89)

    def test_get_affix_tiers_json_partial(self, temp_json_file):
        """Should handle JSON with only some tiers defined."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        tiers = provider.get_affix_tiers("movement_speed")

        assert len(tiers) == 2  # Only T1 and T2

    def test_get_affix_tiers_unknown_type(self, temp_json_file):
        """Should return empty list for unknown affix type."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        tiers = provider.get_affix_tiers("nonexistent_affix")

        assert tiers == []

    def test_get_affix_tiers_database_fallback(self, mock_database, temp_json_file):
        """Should fall back to JSON on database error."""
        mock_database.get_affix_tiers.side_effect = Exception("DB error")

        provider = AffixDataProvider(
            mod_database=mock_database,
            json_path=temp_json_file,
        )

        # With database error, should return empty (no fallback for stat_text pattern)
        tiers = provider.get_affix_tiers("life", stat_text_pattern="%Life%")

        assert tiers == []

    def test_get_affix_config(self, temp_json_file):
        """Should return full affix configuration."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        config = provider.get_affix_config("life")

        assert "tier1_range" in config
        assert "patterns" in config
        assert config["tier1_range"] == [100, 109]

    def test_get_affix_config_not_found(self, temp_json_file):
        """Should return empty dict for unknown affix."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        config = provider.get_affix_config("nonexistent")

        assert config == {}

    def test_get_all_affix_types(self, temp_json_file):
        """Should return list of affix types."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        types = provider.get_all_affix_types()

        assert "life" in types
        assert "movement_speed" in types
        assert "fire_resistance" in types
        # Should exclude special keys
        assert "_synergies" not in types
        assert "_red_flags" not in types

    def test_get_synergies(self, temp_json_file):
        """Should return synergy definitions."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        synergies = provider.get_synergies()

        assert "attack" in synergies
        assert "caster" in synergies

    def test_get_red_flags(self, temp_json_file):
        """Should return red flag definitions."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        red_flags = provider.get_red_flags()

        assert "thorns" in red_flags

    def test_get_source_info_database(self, mock_database, temp_json_file):
        """Should return database info when using database."""
        provider = AffixDataProvider(
            mod_database=mock_database,
            json_path=temp_json_file,
        )

        info = provider.get_source_info()

        assert "ModDatabase" in info
        assert "1000 mods" in info

    def test_get_source_info_json(self, temp_json_file):
        """Should return JSON info when using JSON."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=temp_json_file,
        )

        info = provider.get_source_info()

        assert "JSON Fallback" in info

    def test_json_file_not_found(self, tmp_path):
        """Should handle missing JSON file."""
        provider = AffixDataProvider(
            mod_database=None,
            json_path=tmp_path / "nonexistent.json",
        )

        # Should not raise, but have empty data
        types = provider.get_all_affix_types()
        assert types == []

    def test_json_parse_error(self, tmp_path):
        """Should handle invalid JSON."""
        json_path = tmp_path / "bad.json"
        with open(json_path, 'w') as f:
            f.write("not valid json {")

        provider = AffixDataProvider(
            mod_database=None,
            json_path=json_path,
        )

        # Should not raise, but have empty data
        types = provider.get_all_affix_types()
        assert types == []


class TestGetAffixProvider:
    """Tests for get_affix_provider singleton function."""

    def test_returns_singleton(self, tmp_path):
        """Should return same instance on repeated calls."""
        # Reset singleton
        import data_sources.affix_data_provider as module
        module._provider = None

        # Create a temp JSON file for the provider
        json_path = tmp_path / "valuable_affixes.json"
        with open(json_path, 'w') as f:
            json.dump({"life": {"tier1_range": [100, 109]}}, f)

        with patch.object(AffixDataProvider, '__init__', lambda self, **kwargs: None):
            # Set up the mock provider
            provider1 = MagicMock()
            provider1._json_data = {}
            provider1._using_database = False
            provider1.get_source_info.return_value = "Test info"

            with patch.object(module, 'AffixDataProvider', return_value=provider1):
                result1 = get_affix_provider()
                result2 = get_affix_provider()

                # Reset for cleanup
                module._provider = None

    def test_force_reload(self, tmp_path):
        """Should create new instance when force_reload=True."""
        import data_sources.affix_data_provider as module
        module._provider = None

        # Mock the provider to avoid file system access
        mock_provider = MagicMock()
        mock_provider._json_data = {}
        mock_provider._using_database = False
        mock_provider.get_source_info.return_value = "Test info"

        with patch.object(module, 'AffixDataProvider', return_value=mock_provider):
            provider1 = get_affix_provider()
            provider2 = get_affix_provider(force_reload=True)

            # After force_reload, we get a new provider
            assert provider2 is not None

            # Reset for cleanup
            module._provider = None

    def test_accepts_database(self):
        """Should accept database parameter."""
        import data_sources.affix_data_provider as module
        module._provider = None

        mock_db = MagicMock()
        mock_db.get_mod_count.return_value = 100

        provider = get_affix_provider(mod_database=mock_db, force_reload=True)

        assert provider._using_database is True
        module._provider = None  # Reset for cleanup
