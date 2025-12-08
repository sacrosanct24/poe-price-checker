"""Tests for core/build_summarizer.py - Build summary generation for AI context."""

import json
import pytest
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch

from core.build_summarizer import (
    GearSlotSummary,
    BuildSummary,
    BuildSummarizer,
    get_build_summary,
    cache_build_summary,
    clear_summary_cache,
    save_summary_to_file,
)


# =============================================================================
# Mock PoB Types (for testing without full PoB integration)
# =============================================================================


@dataclass
class MockPoBItem:
    """Mock PoB item for testing."""

    name: str = "Test Item"
    base_type: str = "Test Base"
    rarity: str = "Rare"
    explicit_mods: List[str] = field(default_factory=list)
    sockets: str = ""


@dataclass
class MockPoBBuild:
    """Mock PoB build for testing."""

    display_name: str = "Test Build"
    class_name: str = "Witch"
    ascendancy: str = "Necromancer"
    level: int = 90
    main_skill: str = "Summon Raging Spirit"
    stats: Dict[str, float] = field(default_factory=dict)
    items: Dict[str, MockPoBItem] = field(default_factory=dict)
    skills: List[str] = field(default_factory=list)


# =============================================================================
# GearSlotSummary Tests
# =============================================================================


class TestGearSlotSummary:
    """Tests for GearSlotSummary dataclass."""

    def test_create_basic_summary(self):
        """Should create summary with required fields."""
        summary = GearSlotSummary(
            slot="Helmet",
            item_name="Bone Helmet",
            base_type="Bone Helmet",
            rarity="Rare",
        )
        assert summary.slot == "Helmet"
        assert summary.item_name == "Bone Helmet"
        assert summary.rarity == "Rare"

    def test_default_values(self):
        """Should have sensible defaults."""
        summary = GearSlotSummary(
            slot="Ring 1",
            item_name="Ruby Ring",
            base_type="Ruby Ring",
            rarity="Magic",
        )
        assert summary.key_mods == []
        assert summary.sockets == ""
        assert summary.is_empty is False

    def test_empty_slot(self):
        """Should track empty slots."""
        summary = GearSlotSummary(
            slot="Amulet",
            item_name="",
            base_type="",
            rarity="",
            is_empty=True,
        )
        assert summary.is_empty is True

    def test_with_key_mods(self):
        """Should store key mods."""
        summary = GearSlotSummary(
            slot="Body Armour",
            item_name="Astral Plate",
            base_type="Astral Plate",
            rarity="Rare",
            key_mods=["+100 to maximum Life", "+40% to Fire Resistance"],
        )
        assert len(summary.key_mods) == 2
        assert "+100 to maximum Life" in summary.key_mods


# =============================================================================
# BuildSummary Tests
# =============================================================================


class TestBuildSummary:
    """Tests for BuildSummary dataclass."""

    @pytest.fixture
    def basic_summary(self):
        """Create a basic build summary."""
        return BuildSummary(
            name="RF Juggernaut",
            class_name="Marauder",
            ascendancy="Juggernaut",
            level=95,
            main_skill="Righteous Fire",
            life=6500,
            energy_shield=0,
            fire_res=80,
            cold_res=75,
            lightning_res=75,
            chaos_res=20,
            total_dps=500000,
            playstyle="Spell",
            damage_type="Fire",
            defense_focus="Life",
        )

    def test_create_summary(self, basic_summary):
        """Should create summary with all fields."""
        assert basic_summary.name == "RF Juggernaut"
        assert basic_summary.ascendancy == "Juggernaut"
        assert basic_summary.level == 95
        assert basic_summary.life == 6500

    def test_to_dict(self, basic_summary):
        """Should convert to dictionary."""
        d = basic_summary.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "RF Juggernaut"
        assert d["life"] == 6500
        assert d["fire_res"] == 80

    def test_to_json(self, basic_summary):
        """Should convert to JSON string."""
        j = basic_summary.to_json()
        assert isinstance(j, str)
        parsed = json.loads(j)
        assert parsed["name"] == "RF Juggernaut"
        assert parsed["level"] == 95

    def test_to_json_with_indent(self, basic_summary):
        """Should format JSON with custom indent."""
        j = basic_summary.to_json(indent=4)
        # Should have 4-space indentation
        assert "    " in j

    def test_to_markdown(self, basic_summary):
        """Should generate markdown summary."""
        md = basic_summary.to_markdown()
        assert isinstance(md, str)
        assert "# Build: RF Juggernaut" in md
        assert "Juggernaut" in md
        assert "Life: 6,500" in md
        assert "Fire: 80%" in md

    def test_to_markdown_includes_sections(self, basic_summary):
        """Markdown should have expected sections."""
        md = basic_summary.to_markdown()
        assert "## Defenses" in md
        assert "## Resistances" in md
        assert "## Attributes" in md
        assert "## Current Gear" in md

    def test_to_markdown_with_offense(self, basic_summary):
        """Markdown should include offense section when DPS is set."""
        md = basic_summary.to_markdown()
        assert "## Offense" in md
        assert "500,000" in md  # Total DPS formatted

    def test_to_markdown_with_empty_slots(self):
        """Markdown should show empty slots."""
        summary = BuildSummary(
            name="Test",
            class_name="Test",
            ascendancy="Test",
            level=1,
            main_skill="Test",
            empty_slots=["Amulet", "Ring 2"],
        )
        md = summary.to_markdown()
        assert "Empty Slots" in md
        assert "Amulet" in md

    def test_to_markdown_with_upgrade_priorities(self):
        """Markdown should show upgrade priorities."""
        summary = BuildSummary(
            name="Test",
            class_name="Test",
            ascendancy="Test",
            level=1,
            main_skill="Test",
            upgrade_priorities=["Cap resistances", "Get more life"],
        )
        md = summary.to_markdown()
        assert "## Upgrade Priorities" in md
        assert "1. Cap resistances" in md
        assert "2. Get more life" in md

    def test_to_compact_context(self, basic_summary):
        """Should generate compact context string."""
        ctx = basic_summary.to_compact_context()
        assert isinstance(ctx, str)
        assert "Juggernaut" in ctx
        assert "Lv95" in ctx
        assert "Righteous Fire" in ctx
        assert "6,500" in ctx  # Life formatted
        assert "|" in ctx  # Delimiter


# =============================================================================
# BuildSummarizer Tests
# =============================================================================


class TestBuildSummarizer:
    """Tests for BuildSummarizer class."""

    @pytest.fixture
    def summarizer(self):
        """Create a BuildSummarizer instance."""
        return BuildSummarizer()

    @pytest.fixture
    def mock_build(self):
        """Create a mock build for testing."""
        build = MockPoBBuild(
            display_name="LS Raider",
            class_name="Ranger",
            ascendancy="Raider",
            level=92,
            main_skill="Lightning Strike",
            stats={
                "Life": 4500,
                "EnergyShield": 200,
                "Armour": 3000,
                "Evasion": 25000,
                "FireResist": 75,
                "ColdResist": 80,
                "LightningResist": 75,
                "ChaosResist": -10,
                "TotalDPS": 2000000,
                "Speed": 8.5,
                "CritChance": 75.0,
                "CritMultiplier": 450,
                "Str": 100,
                "Dex": 300,
                "Int": 80,
            },
            items={
                "Weapon 1": MockPoBItem(
                    name="Imperial Claw",
                    base_type="Imperial Claw",
                    rarity="Rare",
                    explicit_mods=[
                        "Adds 50 to 100 Physical Damage",
                        "+35% to Critical Strike Multiplier",
                        "20% increased Attack Speed",
                    ],
                ),
                "Helmet": MockPoBItem(
                    name="Blizzard Crown",
                    base_type="Blizzard Crown",
                    rarity="Rare",
                    explicit_mods=["+100 to maximum Life", "+40% to Fire Resistance"],
                ),
            },
            skills=["Lightning Strike", "Ancestral Call", "Hatred", "Grace", "Precision"],
        )
        return build

    def test_summarize_build_basic(self, summarizer, mock_build):
        """Should extract basic build info."""
        summary = summarizer.summarize_build(mock_build)

        assert summary.name == "LS Raider"
        assert summary.class_name == "Ranger"
        assert summary.ascendancy == "Raider"
        assert summary.level == 92
        assert summary.main_skill == "Lightning Strike"

    def test_summarize_build_extracts_stats(self, summarizer, mock_build):
        """Should extract defense stats."""
        summary = summarizer.summarize_build(mock_build)

        assert summary.life == 4500
        assert summary.energy_shield == 200
        assert summary.evasion == 25000
        assert summary.armour == 3000

    def test_summarize_build_extracts_resistances(self, summarizer, mock_build):
        """Should extract resistances."""
        summary = summarizer.summarize_build(mock_build)

        assert summary.fire_res == 75
        assert summary.cold_res == 80
        assert summary.lightning_res == 75
        assert summary.chaos_res == -10

    def test_summarize_build_extracts_offense(self, summarizer, mock_build):
        """Should extract offense stats."""
        summary = summarizer.summarize_build(mock_build)

        assert summary.total_dps == 2000000
        assert summary.attack_speed == 8.5
        assert summary.crit_chance == 75.0
        assert summary.crit_multi == 450

    def test_summarize_build_extracts_attributes(self, summarizer, mock_build):
        """Should extract attributes."""
        summary = summarizer.summarize_build(mock_build)

        assert summary.strength == 100
        assert summary.dexterity == 300
        assert summary.intelligence == 80

    def test_summarize_build_extracts_gear(self, summarizer, mock_build):
        """Should extract gear info."""
        summary = summarizer.summarize_build(mock_build)

        assert len(summary.gear_slots) > 0
        weapon_slots = [g for g in summary.gear_slots if g.slot == "Weapon 1"]
        assert len(weapon_slots) == 1
        assert weapon_slots[0].item_name == "Imperial Claw"

    def test_summarize_build_extracts_key_mods(self, summarizer, mock_build):
        """Should extract key mods from gear."""
        summary = summarizer.summarize_build(mock_build)

        weapon = next(g for g in summary.gear_slots if g.slot == "Weapon 1")
        # Should find damage and crit mods
        assert len(weapon.key_mods) > 0

    def test_summarize_build_tracks_empty_slots(self, summarizer, mock_build):
        """Should track empty gear slots."""
        summary = summarizer.summarize_build(mock_build)

        # Build only has Weapon 1 and Helmet
        assert "Body Armour" in summary.empty_slots
        assert "Gloves" in summary.empty_slots
        assert "Boots" in summary.empty_slots

    def test_summarize_build_extracts_skills(self, summarizer, mock_build):
        """Should extract active skills."""
        summary = summarizer.summarize_build(mock_build)

        assert "Lightning Strike" in summary.active_skills
        assert "Ancestral Call" in summary.active_skills

    def test_summarize_build_detects_auras(self, summarizer, mock_build):
        """Should detect aura skills."""
        summary = summarizer.summarize_build(mock_build)

        # Build has Hatred, Grace, Precision
        assert len(summary.auras) > 0
        assert any("Hatred" in a for a in summary.auras)

    def test_summarize_build_detects_playstyle(self, summarizer, mock_build):
        """Should detect attack playstyle."""
        summary = summarizer.summarize_build(mock_build)

        assert summary.playstyle == "Attack"

    def test_summarize_build_detects_defense_focus(self, summarizer, mock_build):
        """Should detect defense focus (evasion for this build)."""
        summary = summarizer.summarize_build(mock_build)

        assert summary.defense_focus == "Evasion"

    def test_summarize_build_generates_priorities(self, summarizer, mock_build):
        """Should generate upgrade priorities."""
        summary = summarizer.summarize_build(mock_build)

        # Build has negative chaos res, should suggest improving
        assert len(summary.upgrade_priorities) > 0
        assert any("Chaos" in p for p in summary.upgrade_priorities)

    def test_summarize_build_with_custom_name(self, summarizer, mock_build):
        """Should use custom name if provided."""
        summary = summarizer.summarize_build(mock_build, name="My Custom Build")
        assert summary.name == "My Custom Build"

    def test_detect_minion_playstyle(self, summarizer):
        """Should detect minion playstyle."""
        build = MockPoBBuild(main_skill="Summon Raging Spirit", stats={})
        summary = summarizer.summarize_build(build)
        assert summary.playstyle == "Minion"

    def test_detect_totem_playstyle(self, summarizer):
        """Should detect totem playstyle."""
        build = MockPoBBuild(main_skill="Ballista Totem", stats={})
        summary = summarizer.summarize_build(build)
        assert summary.playstyle == "Totem"

    def test_detect_trap_playstyle(self, summarizer):
        """Should detect trap/mine playstyle."""
        build = MockPoBBuild(main_skill="Lightning Trap", stats={})
        summary = summarizer.summarize_build(build)
        assert summary.playstyle == "Trap/Mine"

    def test_detect_spell_playstyle(self, summarizer):
        """Should detect spell playstyle from cast speed."""
        build = MockPoBBuild(
            main_skill="Arc",
            stats={"CastSpeed": 5.0, "Speed": 1.0},
        )
        summary = summarizer.summarize_build(build)
        assert summary.playstyle == "Spell"

    def test_detect_fire_damage_type(self, summarizer):
        """Should detect fire damage type from main skill."""
        build = MockPoBBuild(main_skill="Fireball", stats={})
        summary = summarizer.summarize_build(build)
        assert summary.damage_type == "Fire"

    def test_detect_cold_damage_type(self, summarizer):
        """Should detect cold damage type from main skill."""
        build = MockPoBBuild(main_skill="Ice Shot", stats={})
        summary = summarizer.summarize_build(build)
        assert summary.damage_type == "Cold"

    def test_detect_damage_type_from_stats(self, summarizer):
        """Should detect damage type from DPS stats."""
        build = MockPoBBuild(
            main_skill="Attack",
            stats={"LightningDPS": 500000, "PhysicalDPS": 100000},
        )
        summary = summarizer.summarize_build(build)
        assert summary.damage_type == "Lightning"

    def test_detect_es_defense_focus(self, summarizer):
        """Should detect ES defense focus."""
        build = MockPoBBuild(stats={"Life": 1000, "EnergyShield": 8000})
        summary = summarizer.summarize_build(build)
        assert summary.defense_focus == "ES"

    def test_detect_hybrid_defense_focus(self, summarizer):
        """Should detect hybrid defense focus."""
        build = MockPoBBuild(stats={"Life": 4000, "EnergyShield": 3000})
        summary = summarizer.summarize_build(build)
        assert summary.defense_focus == "Hybrid"

    def test_detect_armour_defense_focus(self, summarizer):
        """Should detect armour defense focus."""
        build = MockPoBBuild(stats={"Life": 5000, "Armour": 50000, "Evasion": 5000})
        summary = summarizer.summarize_build(build)
        assert summary.defense_focus == "Armour"


# =============================================================================
# Cache Functions Tests
# =============================================================================


class TestBuildSummaryCache:
    """Tests for build summary caching functions."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_summary_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_summary_cache()

    def test_cache_and_retrieve(self):
        """Should cache and retrieve summaries."""
        summary = BuildSummary(
            name="Test",
            class_name="Test",
            ascendancy="Test",
            level=1,
            main_skill="Test",
        )
        cache_build_summary("test_profile", summary)

        retrieved = get_build_summary("test_profile")
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_get_missing_returns_none(self):
        """Should return None for missing profiles."""
        result = get_build_summary("nonexistent")
        assert result is None

    def test_clear_cache(self):
        """Should clear all cached summaries."""
        summary = BuildSummary(
            name="Test",
            class_name="Test",
            ascendancy="Test",
            level=1,
            main_skill="Test",
        )
        cache_build_summary("test", summary)

        clear_summary_cache()
        assert get_build_summary("test") is None


# =============================================================================
# File Operations Tests
# =============================================================================


class TestSaveSummaryToFile:
    """Tests for save_summary_to_file function."""

    @pytest.fixture
    def summary(self):
        """Create test summary."""
        return BuildSummary(
            name="Test Build",
            class_name="Witch",
            ascendancy="Necromancer",
            level=90,
            main_skill="SRS",
            life=5000,
        )

    def test_save_json(self, summary, tmp_path):
        """Should save summary as JSON."""
        path = tmp_path / "summary.json"
        result = save_summary_to_file(summary, path, format="json")

        assert result is True
        assert path.exists()

        content = json.loads(path.read_text())
        assert content["name"] == "Test Build"
        assert content["life"] == 5000

    def test_save_markdown(self, summary, tmp_path):
        """Should save summary as markdown."""
        path = tmp_path / "summary.md"
        result = save_summary_to_file(summary, path, format="markdown")

        assert result is True
        assert path.exists()

        content = path.read_text()
        assert "# Build: Test Build" in content
        assert "5,000" in content  # Formatted life

    def test_save_creates_directories(self, summary, tmp_path):
        """Should create parent directories if needed."""
        path = tmp_path / "nested" / "dir" / "summary.json"
        result = save_summary_to_file(summary, path, format="json")

        assert result is True
        assert path.exists()

    def test_save_unknown_format_returns_false(self, summary, tmp_path):
        """Should return False for unknown format."""
        path = tmp_path / "summary.txt"
        result = save_summary_to_file(summary, path, format="txt")

        assert result is False
        assert not path.exists()

    def test_save_handles_write_error(self, summary, tmp_path):
        """Should handle write errors gracefully."""
        # Try to write to an invalid path
        path = tmp_path / "\x00invalid"  # Invalid filename character
        result = save_summary_to_file(summary, path, format="json")

        # Should return False, not raise
        assert result is False
