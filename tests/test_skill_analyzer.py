"""
Tests for Skill Analyzer.

Tests:
- Skill tag detection from name
- Skill affinity generation
- Affix multiplier calculations
- Integration with archetype
"""
import pytest
from core.skill_analyzer import (
    SkillAnalyzer,
    SkillInfo,
    SkillAffinity,
    analyze_skill,
    SKILL_TAG_DATABASE,
    AFFIX_AFFINITIES,
)
from core.build_archetype import (
    detect_archetype,
    get_combined_weight_multiplier,
    get_skill_valuable_affixes,
)


class TestSkillInfo:
    """Tests for SkillInfo dataclass."""

    def test_from_name_cyclone(self):
        """Test creating SkillInfo for Cyclone."""
        info = SkillInfo.from_name("Cyclone")
        assert "attack" in info.tags
        assert "melee" in info.tags
        assert "physical" in info.tags
        assert info.primary_element == "physical"

    def test_from_name_arc(self):
        """Test creating SkillInfo for Arc."""
        info = SkillInfo.from_name("Arc")
        assert "spell" in info.tags
        assert "lightning" in info.tags
        assert info.primary_element == "lightning"

    def test_from_name_righteous_fire(self):
        """Test creating SkillInfo for Righteous Fire."""
        info = SkillInfo.from_name("Righteous Fire")
        assert "spell" in info.tags
        assert "fire" in info.tags
        assert "dot" in info.tags

    def test_from_name_unknown_skill(self):
        """Test creating SkillInfo for unknown skill."""
        info = SkillInfo.from_name("Unknown Skill ABC")
        # Should create with empty tags
        assert len(info.tags) == 0

    def test_case_insensitive(self):
        """Test skill lookup is case-insensitive."""
        info1 = SkillInfo.from_name("CYCLONE")
        info2 = SkillInfo.from_name("cyclone")
        assert info1.tags == info2.tags


class TestSkillAnalyzer:
    """Tests for SkillAnalyzer class."""

    def test_cyclone_analyzer(self):
        """Test analyzing Cyclone skill."""
        analyzer = SkillAnalyzer("Cyclone")
        summary = analyzer.get_skill_summary()

        assert "Cyclone" in summary
        assert "attack" in summary.lower()
        assert "melee" in summary.lower()

    def test_arc_analyzer(self):
        """Test analyzing Arc skill."""
        analyzer = SkillAnalyzer("Arc")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "spell" in affinity.skill_tags
        assert "lightning" in affinity.skill_tags
        assert affinity.primary_element == "lightning"

    def test_get_valuable_affixes_cyclone(self):
        """Test valuable affixes for Cyclone."""
        analyzer = SkillAnalyzer("Cyclone")
        valuable = analyzer.get_valuable_affixes()

        affix_names = [a for a, _ in valuable]
        # Physical attack build should value these
        assert "physical_damage" in affix_names or "attack_speed" in affix_names
        assert "melee_damage" in affix_names or "area_damage" in affix_names

    def test_get_valuable_affixes_arc(self):
        """Test valuable affixes for Arc."""
        analyzer = SkillAnalyzer("Arc")
        valuable = analyzer.get_valuable_affixes()

        affix_names = [a for a, _ in valuable]
        assert "lightning_damage" in affix_names
        assert "spell_damage" in affix_names or "cast_speed" in affix_names

    def test_affix_multiplier_attack_skill(self):
        """Test affix multipliers for attack skill."""
        analyzer = SkillAnalyzer("Cyclone")

        # Attack speed should be valuable
        as_mult = analyzer.get_affix_multiplier("attack_speed")
        assert as_mult > 1.0

        # Cast speed should be penalized
        cs_mult = analyzer.get_affix_multiplier("cast_speed")
        assert cs_mult < 1.0

    def test_affix_multiplier_spell_skill(self):
        """Test affix multipliers for spell skill."""
        analyzer = SkillAnalyzer("Arc")

        # Cast speed should be valuable
        cs_mult = analyzer.get_affix_multiplier("cast_speed")
        assert cs_mult > 1.0

        # Attack speed should be penalized
        as_mult = analyzer.get_affix_multiplier("attack_speed")
        assert as_mult < 1.0

    def test_affix_multiplier_minion_skill(self):
        """Test affix multipliers for minion skill."""
        analyzer = SkillAnalyzer("Raise Zombie")

        # Minion damage should be valuable
        md_mult = analyzer.get_affix_multiplier("minion_damage")
        assert md_mult > 1.0

        # Cast/attack speed should be penalized
        as_mult = analyzer.get_affix_multiplier("attack_speed")
        assert as_mult < 1.0

    def test_unknown_affix_returns_neutral(self):
        """Test unknown affix returns 1.0 multiplier."""
        analyzer = SkillAnalyzer("Cyclone")
        mult = analyzer.get_affix_multiplier("unknown_affix_xyz")
        assert mult == 1.0

    def test_empty_skill_name(self):
        """Test analyzer with empty skill name."""
        analyzer = SkillAnalyzer("")
        affinity = analyzer.get_affinity()
        assert affinity is None

        # Should return neutral multiplier
        mult = analyzer.get_affix_multiplier("life")
        assert mult == 1.0


class TestSkillAffinity:
    """Tests for SkillAffinity dataclass."""

    def test_is_valuable(self):
        """Test is_valuable method."""
        affinity = SkillAffinity(
            skill_name="Test",
            skill_tags={"attack"},
            primary_element=None,
            valuable_affixes={"attack_speed": 1.5, "melee_damage": 1.4},
            anti_affixes={"cast_speed"},
        )

        assert affinity.is_valuable("attack_speed")
        assert not affinity.is_valuable("cast_speed")
        assert not affinity.is_valuable("unknown")

    def test_is_anti(self):
        """Test is_anti method."""
        affinity = SkillAffinity(
            skill_name="Test",
            skill_tags={"spell"},
            primary_element=None,
            valuable_affixes={"cast_speed": 1.5},
            anti_affixes={"attack_speed", "melee_damage"},
        )

        assert affinity.is_anti("attack_speed")
        assert affinity.is_anti("melee_damage")
        assert not affinity.is_anti("cast_speed")


class TestAnalyzeSkillFunction:
    """Tests for convenience function."""

    def test_analyze_cyclone(self):
        """Test analyze_skill with Cyclone."""
        affinity = analyze_skill("Cyclone")

        assert affinity.skill_name == "Cyclone"
        assert "attack" in affinity.skill_tags
        assert affinity.primary_element == "physical"

    def test_analyze_unknown(self):
        """Test analyze_skill with unknown skill."""
        affinity = analyze_skill("Unknown Skill XYZ")

        assert affinity.skill_name == "Unknown Skill XYZ"
        assert len(affinity.valuable_affixes) == 0


class TestArchetypeIntegration:
    """Tests for integration with build archetype."""

    def test_archetype_includes_main_skill(self):
        """Test archetype includes main skill."""
        stats = {"Life": 5000}
        arch = detect_archetype(stats, "Cyclone")

        assert arch.main_skill == "Cyclone"
        assert "Cyclone" in arch.get_summary()

    def test_combined_weight_multiplier_attack_build(self):
        """Test combined weights for attack build."""
        stats = {"Life": 5000, "CritChance": 40}
        arch = detect_archetype(stats, "Cyclone")

        # Attack speed should be boosted
        as_mult = get_combined_weight_multiplier(arch, "attack_speed")
        assert as_mult > 1.0

        # Cast speed should be penalized
        cs_mult = get_combined_weight_multiplier(arch, "cast_speed")
        assert cs_mult < 1.0

    def test_combined_weight_multiplier_spell_build(self):
        """Test combined weights for spell build."""
        stats = {"Life": 3000, "EnergyShield": 5000}
        arch = detect_archetype(stats, "Arc")

        # Cast speed should be boosted
        cs_mult = get_combined_weight_multiplier(arch, "cast_speed")
        assert cs_mult >= 1.0  # At least neutral or boosted

    def test_combined_without_main_skill(self):
        """Test combined weights without main skill."""
        stats = {"Life": 5000}
        arch = detect_archetype(stats, "")

        # Should just return archetype weight
        mult = get_combined_weight_multiplier(arch, "life")
        assert mult >= 1.0  # Life builds value life

    def test_get_skill_valuable_affixes(self):
        """Test getting valuable affixes for a skill."""
        affixes = get_skill_valuable_affixes("Cyclone")

        assert len(affixes) > 0
        assert any("attack" in a or "physical" in a or "melee" in a for a in affixes)

    def test_get_skill_valuable_affixes_empty(self):
        """Test getting valuable affixes with empty skill."""
        affixes = get_skill_valuable_affixes("")
        assert len(affixes) == 0


class TestSkillTagDatabase:
    """Tests for skill tag database coverage."""

    def test_has_common_skills(self):
        """Test database has common skills."""
        common_skills = [
            "cyclone", "arc", "fireball", "ice nova",
            "tornado shot", "raise zombie", "righteous fire"
        ]
        for skill in common_skills:
            assert skill in SKILL_TAG_DATABASE, f"Missing skill: {skill}"

    def test_skills_have_valid_tags(self):
        """Test all skills have valid tag sets."""
        for skill, tags in SKILL_TAG_DATABASE.items():
            assert isinstance(tags, set), f"{skill} tags should be a set"
            assert len(tags) > 0, f"{skill} should have at least one tag"


class TestAffixAffinities:
    """Tests for affix affinity mappings."""

    def test_attack_affinities(self):
        """Test attack tag has relevant affinities."""
        assert "attack" in AFFIX_AFFINITIES
        attack_affs = AFFIX_AFFINITIES["attack"]
        assert "attack_speed" in attack_affs

    def test_spell_affinities(self):
        """Test spell tag has relevant affinities."""
        assert "spell" in AFFIX_AFFINITIES
        spell_affs = AFFIX_AFFINITIES["spell"]
        assert "cast_speed" in spell_affs
        assert "spell_damage" in spell_affs

    def test_elemental_affinities(self):
        """Test elemental tags have relevant affinities."""
        for elem in ["fire", "cold", "lightning"]:
            assert elem in AFFIX_AFFINITIES
            elem_affs = AFFIX_AFFINITIES[elem]
            assert f"{elem}_damage" in elem_affs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
