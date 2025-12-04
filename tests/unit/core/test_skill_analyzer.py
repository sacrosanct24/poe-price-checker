"""Tests for core/skill_analyzer.py."""
from __future__ import annotations

import pytest


class TestSkillTag:
    """Tests for SkillTag enum."""

    def test_skill_tag_values(self):
        """Test SkillTag enum values."""
        from core.skill_analyzer import SkillTag

        assert SkillTag.ATTACK.value == "attack"
        assert SkillTag.SPELL.value == "spell"
        assert SkillTag.MELEE.value == "melee"
        assert SkillTag.PROJECTILE.value == "projectile"
        assert SkillTag.FIRE.value == "fire"
        assert SkillTag.COLD.value == "cold"
        assert SkillTag.LIGHTNING.value == "lightning"
        assert SkillTag.CHAOS.value == "chaos"
        assert SkillTag.PHYSICAL.value == "physical"
        assert SkillTag.DOT.value == "dot"
        assert SkillTag.MINION.value == "minion"
        assert SkillTag.TOTEM.value == "totem"
        assert SkillTag.TRAP.value == "trap"
        assert SkillTag.MINE.value == "mine"
        assert SkillTag.BRAND.value == "brand"

    def test_skill_tag_string_inheritance(self):
        """Test SkillTag inherits from str."""
        from core.skill_analyzer import SkillTag

        # Should be usable as string
        assert "attack" in SkillTag.ATTACK
        assert SkillTag.FIRE == "fire"


class TestSkillInfo:
    """Tests for SkillInfo dataclass."""

    def test_skill_info_creation(self):
        """Test creating SkillInfo."""
        from core.skill_analyzer import SkillInfo

        info = SkillInfo(
            name="Arc",
            tags={"spell", "lightning"},
            primary_element="lightning",
            is_main_skill=True,
        )

        assert info.name == "Arc"
        assert "spell" in info.tags
        assert "lightning" in info.tags
        assert info.primary_element == "lightning"
        assert info.is_main_skill is True

    def test_skill_info_defaults(self):
        """Test SkillInfo default values."""
        from core.skill_analyzer import SkillInfo

        info = SkillInfo(name="Test")

        assert info.name == "Test"
        assert info.tags == set()
        assert info.primary_element is None
        assert info.is_main_skill is False

    def test_skill_info_from_name_known_skill(self):
        """Test from_name with known skill."""
        from core.skill_analyzer import SkillInfo

        info = SkillInfo.from_name("Cyclone")

        assert info.name == "Cyclone"
        assert "attack" in info.tags
        assert "melee" in info.tags
        assert "area" in info.tags
        assert "physical" in info.primary_element

    def test_skill_info_from_name_unknown_skill(self):
        """Test from_name with unknown skill."""
        from core.skill_analyzer import SkillInfo

        info = SkillInfo.from_name("Unknown Skill Name")

        assert info.name == "Unknown Skill Name"
        assert info.tags == set()

    def test_skill_info_from_name_case_insensitive(self):
        """Test from_name is case insensitive."""
        from core.skill_analyzer import SkillInfo

        info1 = SkillInfo.from_name("arc")
        info2 = SkillInfo.from_name("ARC")
        info3 = SkillInfo.from_name("Arc")

        assert info1.tags == info2.tags == info3.tags


class TestSkillTagDatabase:
    """Tests for SKILL_TAG_DATABASE."""

    def test_database_has_common_skills(self):
        """Test database contains common skills."""
        from core.skill_analyzer import SKILL_TAG_DATABASE

        assert "cyclone" in SKILL_TAG_DATABASE
        assert "arc" in SKILL_TAG_DATABASE
        assert "fireball" in SKILL_TAG_DATABASE
        assert "righteous fire" in SKILL_TAG_DATABASE
        assert "raise zombie" in SKILL_TAG_DATABASE

    def test_database_attack_skills(self):
        """Test attack skills have correct tags."""
        from core.skill_analyzer import SKILL_TAG_DATABASE

        # Cyclone is melee attack
        cyclone = SKILL_TAG_DATABASE["cyclone"]
        assert "attack" in cyclone
        assert "melee" in cyclone
        assert "spell" not in cyclone

        # Tornado shot is projectile attack
        tornado = SKILL_TAG_DATABASE["tornado shot"]
        assert "attack" in tornado
        assert "projectile" in tornado

    def test_database_spell_skills(self):
        """Test spell skills have correct tags."""
        from core.skill_analyzer import SKILL_TAG_DATABASE

        # Arc is lightning spell
        arc = SKILL_TAG_DATABASE["arc"]
        assert "spell" in arc
        assert "lightning" in arc

        # Fireball is fire spell
        fireball = SKILL_TAG_DATABASE["fireball"]
        assert "spell" in fireball
        assert "fire" in fireball

    def test_database_minion_skills(self):
        """Test minion skills have correct tags."""
        from core.skill_analyzer import SKILL_TAG_DATABASE

        zombie = SKILL_TAG_DATABASE["raise zombie"]
        assert "minion" in zombie
        assert "spell" in zombie

    def test_database_dot_skills(self):
        """Test DOT skills have correct tags."""
        from core.skill_analyzer import SKILL_TAG_DATABASE

        rf = SKILL_TAG_DATABASE["righteous fire"]
        assert "dot" in rf
        assert "fire" in rf

        ed = SKILL_TAG_DATABASE["essence drain"]
        assert "dot" in ed
        assert "chaos" in ed


class TestDetectElement:
    """Tests for _detect_element function."""

    def test_detect_from_tags(self):
        """Test element detection from tags."""
        from core.skill_analyzer import _detect_element

        assert _detect_element("test", {"fire", "spell"}) == "fire"
        assert _detect_element("test", {"cold", "projectile"}) == "cold"
        assert _detect_element("test", {"lightning"}) == "lightning"
        assert _detect_element("test", {"chaos", "dot"}) == "chaos"
        assert _detect_element("test", {"physical", "melee"}) == "physical"

    def test_detect_from_name_fire(self):
        """Test fire element detection from name."""
        from core.skill_analyzer import _detect_element

        assert _detect_element("fireball", set()) == "fire"
        assert _detect_element("flame surge", set()) == "fire"
        assert _detect_element("burning arrow", set()) == "fire"
        assert _detect_element("ignite damage", set()) == "fire"
        assert _detect_element("magma orb", set()) == "fire"

    def test_detect_from_name_cold(self):
        """Test cold element detection from name."""
        from core.skill_analyzer import _detect_element

        assert _detect_element("ice nova", set()) == "cold"
        assert _detect_element("frost blades", set()) == "cold"
        # "freezing" contains "freeze" so it should match
        assert _detect_element("freeze pulse", set()) == "cold"
        assert _detect_element("cold snap", set()) == "cold"
        assert _detect_element("chill effect", set()) == "cold"

    def test_detect_from_name_lightning(self):
        """Test lightning element detection from name."""
        from core.skill_analyzer import _detect_element

        assert _detect_element("lightning strike", set()) == "lightning"
        assert _detect_element("arc", set()) == "lightning"
        assert _detect_element("spark", set()) == "lightning"
        assert _detect_element("storm call", set()) == "lightning"
        assert _detect_element("shock nova", set()) == "lightning"

    def test_detect_from_name_chaos(self):
        """Test chaos element detection from name."""
        from core.skill_analyzer import _detect_element

        assert _detect_element("chaos damage", set()) == "chaos"
        assert _detect_element("poison strike", set()) == "chaos"
        assert _detect_element("wither", set()) == "chaos"
        assert _detect_element("blight", set()) == "chaos"

    def test_detect_none(self):
        """Test no element detected."""
        from core.skill_analyzer import _detect_element

        assert _detect_element("unknown skill", set()) is None
        assert _detect_element("generic attack", {"attack"}) is None


class TestAffixAffinities:
    """Tests for AFFIX_AFFINITIES."""

    def test_attack_affinities(self):
        """Test attack skill affinities."""
        from core.skill_analyzer import AFFIX_AFFINITIES

        attack = AFFIX_AFFINITIES["attack"]
        assert "attack_speed" in attack
        assert "accuracy" in attack
        assert attack["attack_speed"] > 1.0

    def test_spell_affinities(self):
        """Test spell skill affinities."""
        from core.skill_analyzer import AFFIX_AFFINITIES

        spell = AFFIX_AFFINITIES["spell"]
        assert "cast_speed" in spell
        assert "spell_damage" in spell
        assert spell["cast_speed"] > 1.0

    def test_element_affinities(self):
        """Test elemental affinities."""
        from core.skill_analyzer import AFFIX_AFFINITIES

        fire = AFFIX_AFFINITIES["fire"]
        assert "fire_damage" in fire
        assert "fire_penetration" in fire

        cold = AFFIX_AFFINITIES["cold"]
        assert "cold_damage" in cold

        lightning = AFFIX_AFFINITIES["lightning"]
        assert "lightning_damage" in lightning

    def test_dot_affinities(self):
        """Test DOT affinities."""
        from core.skill_analyzer import AFFIX_AFFINITIES

        dot = AFFIX_AFFINITIES["dot"]
        assert "damage_over_time" in dot
        assert "damage_over_time_multiplier" in dot

    def test_minion_affinities(self):
        """Test minion affinities."""
        from core.skill_analyzer import AFFIX_AFFINITIES

        minion = AFFIX_AFFINITIES["minion"]
        assert "minion_damage" in minion
        assert "minion_life" in minion


class TestSkillAffinity:
    """Tests for SkillAffinity dataclass."""

    def test_skill_affinity_creation(self):
        """Test creating SkillAffinity."""
        from core.skill_analyzer import SkillAffinity

        affinity = SkillAffinity(
            skill_name="Arc",
            skill_tags={"spell", "lightning"},
            primary_element="lightning",
            valuable_affixes={"cast_speed": 1.5, "lightning_damage": 1.5},
            anti_affixes={"attack_speed", "accuracy"},
        )

        assert affinity.skill_name == "Arc"
        assert "spell" in affinity.skill_tags
        assert affinity.primary_element == "lightning"
        assert affinity.valuable_affixes["cast_speed"] == 1.5
        assert "attack_speed" in affinity.anti_affixes

    def test_get_affix_multiplier_valuable(self):
        """Test get_affix_multiplier for valuable affix."""
        from core.skill_analyzer import SkillAffinity

        affinity = SkillAffinity(
            skill_name="Test",
            skill_tags=set(),
            primary_element=None,
            valuable_affixes={"test_affix": 1.5},
            anti_affixes=set(),
        )

        assert affinity.get_affix_multiplier("test_affix") == 1.5

    def test_get_affix_multiplier_unknown(self):
        """Test get_affix_multiplier for unknown affix."""
        from core.skill_analyzer import SkillAffinity

        affinity = SkillAffinity(
            skill_name="Test",
            skill_tags=set(),
            primary_element=None,
            valuable_affixes={},
            anti_affixes=set(),
        )

        assert affinity.get_affix_multiplier("unknown") == 1.0

    def test_is_valuable(self):
        """Test is_valuable method."""
        from core.skill_analyzer import SkillAffinity

        affinity = SkillAffinity(
            skill_name="Test",
            skill_tags=set(),
            primary_element=None,
            valuable_affixes={"good_affix": 1.5},
            anti_affixes=set(),
        )

        assert affinity.is_valuable("good_affix") is True
        assert affinity.is_valuable("other_affix") is False

    def test_is_anti(self):
        """Test is_anti method."""
        from core.skill_analyzer import SkillAffinity

        affinity = SkillAffinity(
            skill_name="Test",
            skill_tags=set(),
            primary_element=None,
            valuable_affixes={},
            anti_affixes={"bad_affix"},
        )

        assert affinity.is_anti("bad_affix") is True
        assert affinity.is_anti("other_affix") is False


class TestSkillAnalyzerInit:
    """Tests for SkillAnalyzer initialization."""

    def test_init_no_skill(self):
        """Test initialization without skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer()

        assert analyzer.main_skill == ""
        assert analyzer._skill_info is None
        assert analyzer._affinity is None

    def test_init_with_skill(self):
        """Test initialization with skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")

        assert analyzer.main_skill == "Arc"
        assert analyzer._skill_info is not None
        assert analyzer._affinity is not None

    def test_init_unknown_skill(self):
        """Test initialization with unknown skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Unknown Skill")

        assert analyzer.main_skill == "Unknown Skill"
        # Should still create info/affinity, just empty
        assert analyzer._skill_info is not None


class TestSkillAnalyzerMethods:
    """Tests for SkillAnalyzer methods."""

    def test_get_affinity(self):
        """Test get_affinity method."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert affinity.skill_name == "Arc"
        assert "spell" in affinity.skill_tags
        assert "lightning" in affinity.skill_tags

    def test_get_affinity_no_skill(self):
        """Test get_affinity with no skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer()
        affinity = analyzer.get_affinity()

        assert affinity is None

    def test_get_skill_info(self):
        """Test get_skill_info method."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Cyclone")
        info = analyzer.get_skill_info()

        assert info is not None
        assert info.name == "Cyclone"
        assert "attack" in info.tags

    def test_get_skill_info_no_skill(self):
        """Test get_skill_info with no skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer()
        info = analyzer.get_skill_info()

        assert info is None

    def test_get_affix_multiplier_valuable(self):
        """Test get_affix_multiplier for valuable affix."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")
        mult = analyzer.get_affix_multiplier("cast_speed")

        assert mult > 1.0

    def test_get_affix_multiplier_anti(self):
        """Test get_affix_multiplier for anti affix."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")  # Spell skill
        mult = analyzer.get_affix_multiplier("attack_speed")

        assert mult == 0.5  # Anti-synergy

    def test_get_affix_multiplier_no_affinity(self):
        """Test get_affix_multiplier with no affinity."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer()
        mult = analyzer.get_affix_multiplier("anything")

        assert mult == 1.0

    def test_get_valuable_affixes(self):
        """Test get_valuable_affixes method."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")
        valuable = analyzer.get_valuable_affixes()

        assert len(valuable) > 0
        # Should be sorted by multiplier descending
        assert valuable[0][1] >= valuable[-1][1]
        # Should include cast_speed for spell
        affix_names = [a[0] for a in valuable]
        assert "cast_speed" in affix_names

    def test_get_valuable_affixes_no_affinity(self):
        """Test get_valuable_affixes with no affinity."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer()
        valuable = analyzer.get_valuable_affixes()

        assert valuable == []

    def test_get_skill_summary(self):
        """Test get_skill_summary method."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")
        summary = analyzer.get_skill_summary()

        assert "Arc" in summary
        assert "spell" in summary.lower() or "[" in summary

    def test_get_skill_summary_no_info(self):
        """Test get_skill_summary with no skill info."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer()
        summary = analyzer.get_skill_summary()

        assert summary == "Unknown skill"

    def test_is_mod_relevant_element_match(self):
        """Test is_mod_relevant with element match."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")  # Lightning skill
        relevant, reason = analyzer.is_mod_relevant("lightning damage")

        assert relevant is True
        assert "lightning" in reason.lower()

    def test_is_mod_relevant_spell_attack_mismatch(self):
        """Test is_mod_relevant with spell/attack mismatch."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")  # Spell skill
        relevant, reason = analyzer.is_mod_relevant("attack damage")

        assert relevant is False
        assert "attack" in reason.lower()

    def test_is_mod_relevant_attack_spell_mismatch(self):
        """Test is_mod_relevant with attack/spell mismatch."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Cyclone")  # Attack skill
        relevant, reason = analyzer.is_mod_relevant("spell damage")

        assert relevant is False
        assert "spell" in reason.lower()

    def test_is_mod_relevant_tag_match(self):
        """Test is_mod_relevant with tag match."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Cyclone")  # Has "area" tag
        relevant, reason = analyzer.is_mod_relevant("area damage")

        assert relevant is True

    def test_is_mod_relevant_no_affinity(self):
        """Test is_mod_relevant with no affinity."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer()
        relevant, reason = analyzer.is_mod_relevant("any mod")

        assert relevant is True
        assert reason == ""


class TestSkillAnalyzerAntiSynergies:
    """Tests for anti-synergy detection."""

    def test_spell_anti_synergies(self):
        """Test spell skills have attack anti-synergies."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Arc")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "attack_speed" in affinity.anti_affixes
        assert "accuracy" in affinity.anti_affixes

    def test_attack_anti_synergies(self):
        """Test attack skills have spell anti-synergies."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Cyclone")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "cast_speed" in affinity.anti_affixes
        assert "spell_damage" in affinity.anti_affixes

    def test_minion_anti_synergies(self):
        """Test minion skills have self-damage anti-synergies."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Raise Zombie")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "attack_speed" in affinity.anti_affixes


class TestAnalyzeSkillFunction:
    """Tests for analyze_skill convenience function."""

    def test_analyze_known_skill(self):
        """Test analyze_skill with known skill."""
        from core.skill_analyzer import analyze_skill

        affinity = analyze_skill("Arc")

        assert affinity.skill_name == "Arc"
        assert "spell" in affinity.skill_tags
        assert len(affinity.valuable_affixes) > 0

    def test_analyze_unknown_skill(self):
        """Test analyze_skill with unknown skill."""
        from core.skill_analyzer import analyze_skill

        affinity = analyze_skill("Completely Unknown Skill")

        assert affinity.skill_name == "Completely Unknown Skill"
        assert affinity.skill_tags == set()
        assert affinity.valuable_affixes == {}
        assert affinity.anti_affixes == set()


class TestIntegration:
    """Integration tests for skill analyzer."""

    def test_attack_skill_full_analysis(self):
        """Test full analysis of an attack skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Lightning Strike")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "attack" in affinity.skill_tags
        assert "melee" in affinity.skill_tags
        assert "projectile" in affinity.skill_tags
        assert "lightning" in affinity.skill_tags
        assert affinity.primary_element == "lightning"

        # Should value attack and lightning mods
        valuable = analyzer.get_valuable_affixes()
        affix_names = [a[0] for a in valuable]
        assert "attack_speed" in affix_names
        assert "lightning_damage" in affix_names

        # Should not value spell mods
        assert "cast_speed" in affinity.anti_affixes

    def test_spell_skill_full_analysis(self):
        """Test full analysis of a spell skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Fireball")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "spell" in affinity.skill_tags
        assert "fire" in affinity.skill_tags
        assert affinity.primary_element == "fire"

        # Should value spell and fire mods
        valuable = analyzer.get_valuable_affixes()
        affix_names = [a[0] for a in valuable]
        assert "cast_speed" in affix_names
        assert "fire_damage" in affix_names

        # Should not value attack mods
        assert "attack_speed" in affinity.anti_affixes

    def test_dot_skill_full_analysis(self):
        """Test full analysis of a DOT skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Righteous Fire")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "dot" in affinity.skill_tags
        assert "fire" in affinity.skill_tags

        # Should value DOT mods
        valuable = analyzer.get_valuable_affixes()
        affix_names = [a[0] for a in valuable]
        assert "damage_over_time" in affix_names or "fire_damage_over_time" in affix_names

    def test_minion_skill_full_analysis(self):
        """Test full analysis of a minion skill."""
        from core.skill_analyzer import SkillAnalyzer

        analyzer = SkillAnalyzer("Raise Zombie")
        affinity = analyzer.get_affinity()

        assert affinity is not None
        assert "minion" in affinity.skill_tags

        # Should value minion mods
        valuable = analyzer.get_valuable_affixes()
        affix_names = [a[0] for a in valuable]
        assert "minion_damage" in affix_names
