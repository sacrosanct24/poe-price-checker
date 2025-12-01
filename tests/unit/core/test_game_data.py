"""Tests for core/game_data.py - Game version, class, and ascendancy data."""

from core.game_data import (
    GameVersion,
    POE1_CLASSES,
    POE2_CLASSES,
    get_classes_for_game,
    get_all_ascendancies,
    get_class_for_ascendancy,
    detect_game_version_from_ascendancy,
    detect_game_version_from_class,
    detect_game_version,
)


class TestGameVersion:
    """Tests for GameVersion enum."""

    def test_poe1_value(self):
        """POE1 should have correct value."""
        assert GameVersion.POE1.value == "poe1"

    def test_poe2_value(self):
        """POE2 should have correct value."""
        assert GameVersion.POE2.value == "poe2"

    def test_display_name_poe1(self):
        """POE1 display name should be full name."""
        assert GameVersion.POE1.display_name == "Path of Exile 1"

    def test_display_name_poe2(self):
        """POE2 display name should be full name."""
        assert GameVersion.POE2.display_name == "Path of Exile 2"

    def test_short_name_poe1(self):
        """POE1 short name should be abbreviated."""
        assert GameVersion.POE1.short_name == "PoE1"

    def test_short_name_poe2(self):
        """POE2 short name should be abbreviated."""
        assert GameVersion.POE2.short_name == "PoE2"


class TestClassInfo:
    """Tests for ClassInfo dataclass."""

    def test_get_ascendancy_exists(self):
        """Should find existing ascendancy."""
        class_info = POE1_CLASSES["Witch"]
        asc = class_info.get_ascendancy("Necromancer")

        assert asc is not None
        assert asc.name == "Necromancer"

    def test_get_ascendancy_case_insensitive(self):
        """Should find ascendancy case-insensitively."""
        class_info = POE1_CLASSES["Witch"]

        assert class_info.get_ascendancy("necromancer") is not None
        assert class_info.get_ascendancy("NECROMANCER") is not None
        assert class_info.get_ascendancy("NeCrOmAnCeR") is not None

    def test_get_ascendancy_not_found(self):
        """Should return None for non-existent ascendancy."""
        class_info = POE1_CLASSES["Witch"]
        assert class_info.get_ascendancy("NonExistent") is None


class TestPOE1Classes:
    """Tests for POE1 class data."""

    def test_has_seven_classes(self):
        """POE1 should have 7 base classes."""
        assert len(POE1_CLASSES) == 7

    def test_scion_has_ascendant(self):
        """Scion should have Ascendant."""
        assert "Scion" in POE1_CLASSES
        assert len(POE1_CLASSES["Scion"].ascendancies) == 1
        assert POE1_CLASSES["Scion"].ascendancies[0].name == "Ascendant"

    def test_marauder_ascendancies(self):
        """Marauder should have 3 ascendancies."""
        marauder = POE1_CLASSES["Marauder"]
        names = [a.name for a in marauder.ascendancies]

        assert len(names) == 3
        assert "Juggernaut" in names
        assert "Berserker" in names
        assert "Chieftain" in names

    def test_all_classes_have_ascendancies(self):
        """All classes should have at least one ascendancy."""
        for class_name, class_info in POE1_CLASSES.items():
            assert len(class_info.ascendancies) >= 1, f"{class_name} has no ascendancies"


class TestPOE2Classes:
    """Tests for POE2 class data."""

    def test_has_expected_classes(self):
        """POE2 should have expected classes."""
        expected = {"Warrior", "Ranger", "Witch", "Mercenary", "Monk", "Sorceress", "Huntress"}
        assert set(POE2_CLASSES.keys()) == expected

    def test_warrior_ascendancies(self):
        """Warrior should have Titan and Warbringer."""
        warrior = POE2_CLASSES["Warrior"]
        names = [a.name for a in warrior.ascendancies]

        assert "Titan" in names
        assert "Warbringer" in names

    def test_witch_ascendancies_poe2(self):
        """POE2 Witch should have Blood Mage and Infernalist."""
        witch = POE2_CLASSES["Witch"]
        names = [a.name for a in witch.ascendancies]

        assert "Blood Mage" in names
        assert "Infernalist" in names


class TestGetClassesForGame:
    """Tests for get_classes_for_game function."""

    def test_returns_poe1_classes(self):
        """Should return POE1 classes for POE1."""
        classes = get_classes_for_game(GameVersion.POE1)
        assert classes is POE1_CLASSES
        assert "Marauder" in classes

    def test_returns_poe2_classes(self):
        """Should return POE2 classes for POE2."""
        classes = get_classes_for_game(GameVersion.POE2)
        assert classes is POE2_CLASSES
        assert "Warrior" in classes


class TestGetAllAscendancies:
    """Tests for get_all_ascendancies function."""

    def test_poe1_ascendancies_sorted(self):
        """Should return sorted POE1 ascendancies."""
        ascs = get_all_ascendancies(GameVersion.POE1)

        assert "Ascendant" in ascs
        assert "Necromancer" in ascs
        assert "Juggernaut" in ascs
        # Should be sorted
        assert ascs == sorted(ascs)

    def test_poe2_ascendancies(self):
        """Should return POE2 ascendancies."""
        ascs = get_all_ascendancies(GameVersion.POE2)

        assert "Titan" in ascs
        assert "Stormweaver" in ascs
        assert "Blood Mage" in ascs


class TestGetClassForAscendancy:
    """Tests for get_class_for_ascendancy function."""

    def test_finds_class_poe1(self):
        """Should find class for POE1 ascendancy."""
        assert get_class_for_ascendancy(GameVersion.POE1, "Necromancer") == "Witch"
        assert get_class_for_ascendancy(GameVersion.POE1, "Juggernaut") == "Marauder"
        assert get_class_for_ascendancy(GameVersion.POE1, "Ascendant") == "Scion"

    def test_finds_class_poe2(self):
        """Should find class for POE2 ascendancy."""
        assert get_class_for_ascendancy(GameVersion.POE2, "Titan") == "Warrior"
        assert get_class_for_ascendancy(GameVersion.POE2, "Stormweaver") == "Sorceress"

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert get_class_for_ascendancy(GameVersion.POE1, "NECROMANCER") == "Witch"
        assert get_class_for_ascendancy(GameVersion.POE1, "necromancer") == "Witch"

    def test_returns_none_for_unknown(self):
        """Should return None for unknown ascendancy."""
        assert get_class_for_ascendancy(GameVersion.POE1, "FakeClass") is None


class TestDetectGameVersionFromAscendancy:
    """Tests for detect_game_version_from_ascendancy function."""

    def test_detects_poe1_only_ascendancies(self):
        """Should detect POE1-only ascendancies."""
        poe1_only = ["Ascendant", "Juggernaut", "Necromancer", "Assassin", "Saboteur"]

        for asc in poe1_only:
            result = detect_game_version_from_ascendancy(asc)
            assert result == GameVersion.POE1, f"{asc} should be POE1"

    def test_detects_poe2_only_ascendancies(self):
        """Should detect POE2-only ascendancies."""
        poe2_only = ["Titan", "Stormweaver", "Blood Mage", "Witchhunter", "Chronomancer"]

        for asc in poe2_only:
            result = detect_game_version_from_ascendancy(asc)
            assert result == GameVersion.POE2, f"{asc} should be POE2"

    def test_returns_none_for_shared_ascendancies(self):
        """Should return None for ascendancies in both games."""
        # Deadeye and Pathfinder exist in both games
        assert detect_game_version_from_ascendancy("Deadeye") is None
        assert detect_game_version_from_ascendancy("Pathfinder") is None

    def test_returns_none_for_empty(self):
        """Should return None for empty string."""
        assert detect_game_version_from_ascendancy("") is None

    def test_case_insensitive(self):
        """Should be case-insensitive."""
        assert detect_game_version_from_ascendancy("NECROMANCER") == GameVersion.POE1
        assert detect_game_version_from_ascendancy("titan") == GameVersion.POE2


class TestDetectGameVersionFromClass:
    """Tests for detect_game_version_from_class function."""

    def test_detects_poe1_only_classes(self):
        """Should detect POE1-only classes."""
        poe1_only = ["Scion", "Marauder", "Duelist", "Templar", "Shadow"]

        for cls in poe1_only:
            result = detect_game_version_from_class(cls)
            assert result == GameVersion.POE1, f"{cls} should be POE1"

    def test_detects_poe2_only_classes(self):
        """Should detect POE2-only classes."""
        poe2_only = ["Warrior", "Mercenary", "Monk", "Sorceress", "Huntress"]

        for cls in poe2_only:
            result = detect_game_version_from_class(cls)
            assert result == GameVersion.POE2, f"{cls} should be POE2"

    def test_returns_none_for_shared_classes(self):
        """Should return None for classes in both games."""
        # Ranger and Witch exist in both games
        assert detect_game_version_from_class("Ranger") is None
        assert detect_game_version_from_class("Witch") is None

    def test_returns_none_for_empty(self):
        """Should return None for empty string."""
        assert detect_game_version_from_class("") is None


class TestDetectGameVersion:
    """Tests for detect_game_version function."""

    def test_prioritizes_ascendancy(self):
        """Should prioritize ascendancy over class when both provided."""
        # Necromancer is POE1-only, even if class is ambiguous
        result = detect_game_version(class_name="Witch", ascendancy="Necromancer")
        assert result == GameVersion.POE1

        # Stormweaver is POE2-only
        result = detect_game_version(class_name="Witch", ascendancy="Stormweaver")
        assert result == GameVersion.POE2

    def test_falls_back_to_class(self):
        """Should use class if ascendancy is ambiguous."""
        # Marauder is POE1-only
        result = detect_game_version(class_name="Marauder", ascendancy="")
        assert result == GameVersion.POE1

        # Warrior is POE2-only
        result = detect_game_version(class_name="Warrior", ascendancy="")
        assert result == GameVersion.POE2

    def test_returns_none_when_ambiguous(self):
        """Should return None when can't determine."""
        # Ranger and Deadeye exist in both games
        result = detect_game_version(class_name="Ranger", ascendancy="Deadeye")
        assert result is None

    def test_returns_none_for_empty_inputs(self):
        """Should return None for empty inputs."""
        assert detect_game_version() is None
        assert detect_game_version(class_name="", ascendancy="") is None
