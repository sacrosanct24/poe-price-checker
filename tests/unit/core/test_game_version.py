"""
Unit tests for core.game_version module - Game version enumeration.

Tests cover:
- GameVersion enum functionality
- String parsing (case insensitive)
- Display name generation
- GameConfig initialization
- Helper methods
"""

import pytest

from core.game_version import GameVersion, GameConfig

pytestmark = pytest.mark.unit


# -------------------------
# GameVersion Enum Tests
# -------------------------

class TestGameVersionEnum:
    """Test GameVersion enum functionality."""

    def test_poe1_value(self):
        """POE1 should have correct value."""
        assert GameVersion.POE1.value == "poe1"

    def test_poe2_value(self):
        """POE2 should have correct value."""
        assert GameVersion.POE2.value == "poe2"

    def test_str_representation(self):
        """String representation should return value."""
        assert str(GameVersion.POE1) == "poe1"
        assert str(GameVersion.POE2) == "poe2"

    def test_display_name_poe1(self):
        """POE1 display name should be human-readable."""
        assert GameVersion.POE1.display_name() == "Path of Exile 1"

    def test_display_name_poe2(self):
        """POE2 display name should be human-readable."""
        assert GameVersion.POE2.display_name() == "Path of Exile 2"

    def test_enum_comparison(self):
        """Enum values should be comparable."""
        # Test that same enum values are equal (using variables to avoid tautology)
        poe1_a = GameVersion.POE1
        poe1_b = GameVersion.POE1
        poe2_a = GameVersion.POE2
        poe2_b = GameVersion.POE2
        assert poe1_a == poe1_b
        assert poe2_a == poe2_b
        assert poe1_a != poe2_a


# -------------------------
# from_string Tests
# -------------------------

class TestGameVersionFromString:
    """Test parsing GameVersion from string."""

    def test_from_string_poe1_lowercase(self):
        """Should parse 'poe1' correctly."""
        version = GameVersion.from_string("poe1")
        assert version == GameVersion.POE1

    def test_from_string_poe2_lowercase(self):
        """Should parse 'poe2' correctly."""
        version = GameVersion.from_string("poe2")
        assert version == GameVersion.POE2

    def test_from_string_poe1_uppercase(self):
        """Should parse 'POE1' correctly (case insensitive)."""
        version = GameVersion.from_string("POE1")
        assert version == GameVersion.POE1

    def test_from_string_poe2_uppercase(self):
        """Should parse 'POE2' correctly (case insensitive)."""
        version = GameVersion.from_string("POE2")
        assert version == GameVersion.POE2

    def test_from_string_mixed_case(self):
        """Should parse mixed case correctly."""
        assert GameVersion.from_string("PoE1") == GameVersion.POE1
        assert GameVersion.from_string("pOe2") == GameVersion.POE2

    def test_from_string_with_whitespace(self):
        """Should handle whitespace correctly."""
        assert GameVersion.from_string("  poe1  ") == GameVersion.POE1
        assert GameVersion.from_string(" POE2 ") == GameVersion.POE2

    def test_from_string_invalid_returns_none(self):
        """Should return None for invalid strings."""
        assert GameVersion.from_string("poe3") is None
        assert GameVersion.from_string("invalid") is None
        assert GameVersion.from_string("") is None

    def test_from_string_with_numbers(self):
        """Should handle strings with extra characters."""
        assert GameVersion.from_string("path of exile 1") is None
        assert GameVersion.from_string("1") is None


# -------------------------
# get_default Tests
# -------------------------

class TestGameVersionGetDefault:
    """Test default game version."""

    def test_get_default_returns_poe1(self):
        """Default should be POE1."""
        default = GameVersion.get_default()
        assert default == GameVersion.POE1


# -------------------------
# GameConfig Initialization Tests
# -------------------------

class TestGameConfigInitialization:
    """Test GameConfig initialization."""

    def test_creates_config_with_defaults(self):
        """Should create config with default values."""
        config = GameConfig(GameVersion.POE1)

        assert config.game_version == GameVersion.POE1
        assert config.league == "Standard"
        assert config.divine_chaos_rate == 1.0

    def test_creates_config_with_custom_league(self):
        """Should create config with custom league."""
        config = GameConfig(
            GameVersion.POE1,
            league="Crucible"
        )

        assert config.league == "Crucible"

    def test_creates_config_with_custom_divine_rate(self):
        """Should create config with custom divine rate."""
        config = GameConfig(
            GameVersion.POE1,
            divine_chaos_rate=250.5
        )

        assert config.divine_chaos_rate == 250.5

    def test_creates_config_for_poe2(self):
        """Should create config for POE2."""
        config = GameConfig(
            GameVersion.POE2,
            league="Standard Settlers",
            divine_chaos_rate=150.0
        )

        assert config.game_version == GameVersion.POE2
        assert config.league == "Standard Settlers"
        assert config.divine_chaos_rate == 150.0


# -------------------------
# GameConfig Methods Tests
# -------------------------

class TestGameConfigMethods:
    """Test GameConfig helper methods."""

    def test_get_api_league_name(self):
        """Should return league name for API calls."""
        config = GameConfig(GameVersion.POE1, league="Crucible")

        assert config.get_api_league_name() == "Crucible"

    def test_is_poe1_returns_true_for_poe1(self):
        """is_poe1 should return True for POE1 config."""
        config = GameConfig(GameVersion.POE1)

        assert config.is_poe1() is True

    def test_is_poe1_returns_false_for_poe2(self):
        """is_poe1 should return False for POE2 config."""
        config = GameConfig(GameVersion.POE2)

        assert config.is_poe1() is False

    def test_is_poe2_returns_true_for_poe2(self):
        """is_poe2 should return True for POE2 config."""
        config = GameConfig(GameVersion.POE2)

        assert config.is_poe2() is True

    def test_is_poe2_returns_false_for_poe1(self):
        """is_poe2 should return False for POE1 config."""
        config = GameConfig(GameVersion.POE1)

        assert config.is_poe2() is False

    def test_repr_contains_important_info(self):
        """repr should contain key information."""
        config = GameConfig(
            GameVersion.POE1,
            league="Crucible",
            divine_chaos_rate=317.2
        )

        repr_str = repr(config)

        assert "GameConfig" in repr_str
        assert "poe1" in repr_str.lower() or "POE1" in repr_str
        assert "Crucible" in repr_str
        assert "317" in repr_str


# -------------------------
# Edge Case Tests
# -------------------------

class TestGameConfigEdgeCases:
    """Test edge cases and special scenarios."""

    def test_config_with_empty_league_name(self):
        """Should handle empty league name."""
        config = GameConfig(GameVersion.POE1, league="")

        assert config.league == ""
        assert config.get_api_league_name() == ""

    def test_config_with_very_high_divine_rate(self):
        """Should handle very high divine rates."""
        config = GameConfig(
            GameVersion.POE1,
            divine_chaos_rate=10000.0
        )

        assert config.divine_chaos_rate == 10000.0

    def test_config_with_zero_divine_rate(self):
        """Should handle zero divine rate."""
        config = GameConfig(
            GameVersion.POE1,
            divine_chaos_rate=0.0
        )

        assert config.divine_chaos_rate == 0.0

    def test_config_with_negative_divine_rate(self):
        """Should accept negative divine rate (even if invalid)."""
        config = GameConfig(
            GameVersion.POE1,
            divine_chaos_rate=-100.0
        )

        # No validation in constructor, so it accepts it
        assert config.divine_chaos_rate == -100.0

    def test_config_with_special_characters_in_league(self):
        """Should handle special characters in league name."""
        config = GameConfig(
            GameVersion.POE1,
            league="Settlers of Kalguur™"
        )

        assert config.league == "Settlers of Kalguur™"
        assert config.get_api_league_name() == "Settlers of Kalguur™"
