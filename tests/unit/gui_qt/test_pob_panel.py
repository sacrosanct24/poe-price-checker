"""
Tests for gui_qt.widgets.pob_panel module.

Tests the embedded PoB character panel widget.
"""

import pytest
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Skip all tests if PyQt6 is not available
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication


# Ensure QApplication exists for widget tests
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@dataclass
class MockPoBItem:
    """Mock PoBItem for testing."""
    slot: str = "Helmet"
    rarity: str = "RARE"
    name: str = "Test Item"
    base_type: str = "Eternal Burgonet"
    item_level: int = 86
    quality: int = 20
    sockets: str = "R-R-R-G"
    implicit_mods: List[str] = field(default_factory=list)
    explicit_mods: List[str] = field(default_factory=list)
    influences: List[str] = field(default_factory=list)


@dataclass
class MockPoBBuild:
    """Mock PoBBuild for testing."""
    class_name: str = "Marauder"
    ascendancy: str = "Juggernaut"
    level: int = 100
    items: Dict[str, MockPoBItem] = field(default_factory=dict)


@dataclass
class MockCharacterProfile:
    """Mock CharacterProfile for testing."""
    name: str = "TestChar"
    build: MockPoBBuild = field(default_factory=MockPoBBuild)


class MockCharacterManager:
    """Mock CharacterManager for testing."""

    def __init__(self, profiles=None, active_profile=None):
        self._profiles = profiles or {}
        self._active_profile = active_profile

    def list_profiles(self) -> List[str]:
        return list(self._profiles.keys())

    def get_profile(self, name: str) -> Optional[MockCharacterProfile]:
        return self._profiles.get(name)

    def get_active_profile(self) -> Optional[MockCharacterProfile]:
        return self._active_profile


class TestPoBPanelCreation:
    """Tests for PoBPanel widget creation."""

    def test_creates_with_character_manager(self, qapp):
        """Panel should create successfully with a character manager."""
        from gui_qt.widgets.pob_panel import PoBPanel

        manager = MockCharacterManager()
        panel = PoBPanel(manager)

        assert panel is not None
        assert panel.character_manager is manager

    def test_creates_with_none_manager(self, qapp):
        """Panel should handle None character manager gracefully."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(None)
        assert panel is not None
        # Should show "(No profiles)" in combo
        assert panel.profile_combo.count() == 1
        assert "No profiles" in panel.profile_combo.itemText(0)

    def test_creates_required_widgets(self, qapp):
        """Panel should create all required UI widgets."""
        from gui_qt.widgets.pob_panel import PoBPanel

        manager = MockCharacterManager()
        panel = PoBPanel(manager)

        assert panel.profile_combo is not None
        assert panel.class_label is not None
        assert panel.equipment_tree is not None
        assert panel.check_selected_btn is not None
        assert panel.check_all_btn is not None


class TestPoBPanelProfileLoading:
    """Tests for profile loading functionality."""

    def test_loads_profile_names_into_combo(self, qapp):
        """Profile names should appear in the combo box."""
        from gui_qt.widgets.pob_panel import PoBPanel

        profiles = {
            "Char1": MockCharacterProfile(name="Char1"),
            "Char2": MockCharacterProfile(name="Char2"),
        }
        manager = MockCharacterManager(profiles=profiles)
        panel = PoBPanel(manager)

        assert panel.profile_combo.count() == 2
        items = [panel.profile_combo.itemText(i) for i in range(panel.profile_combo.count())]
        assert "Char1" in items
        assert "Char2" in items

    def test_selects_active_profile(self, qapp):
        """Active profile should be selected in combo box."""
        from gui_qt.widgets.pob_panel import PoBPanel

        profiles = {
            "Char1": MockCharacterProfile(name="Char1"),
            "Char2": MockCharacterProfile(name="Char2"),
        }
        active = profiles["Char2"]
        manager = MockCharacterManager(profiles=profiles, active_profile=active)
        panel = PoBPanel(manager)

        assert panel.profile_combo.currentText() == "Char2"

    def test_shows_no_profiles_message(self, qapp):
        """Should show message when no profiles exist."""
        from gui_qt.widgets.pob_panel import PoBPanel

        manager = MockCharacterManager(profiles={})
        panel = PoBPanel(manager)

        assert panel.profile_combo.count() == 1
        assert "No profiles" in panel.profile_combo.itemText(0)


class TestPoBPanelProfileDisplay:
    """Tests for profile display functionality."""

    def test_displays_class_and_level(self, qapp):
        """Should display class/ascendancy and level."""
        from gui_qt.widgets.pob_panel import PoBPanel

        build = MockPoBBuild(class_name="Witch", ascendancy="Elementalist", level=95)
        profile = MockCharacterProfile(name="TestChar", build=build)
        profiles = {"TestChar": profile}
        manager = MockCharacterManager(profiles=profiles, active_profile=profile)
        panel = PoBPanel(manager)

        # Trigger profile display
        panel._on_profile_changed("TestChar")

        assert "95" in panel.class_label.text()
        assert "Elementalist" in panel.class_label.text()

    def test_displays_class_without_ascendancy(self, qapp):
        """Should display base class when no ascendancy."""
        from gui_qt.widgets.pob_panel import PoBPanel

        build = MockPoBBuild(class_name="Witch", ascendancy="", level=50)
        profile = MockCharacterProfile(name="TestChar", build=build)
        profiles = {"TestChar": profile}
        manager = MockCharacterManager(profiles=profiles, active_profile=profile)
        panel = PoBPanel(manager)

        panel._on_profile_changed("TestChar")

        assert "50" in panel.class_label.text()
        assert "Witch" in panel.class_label.text()


class TestPoBPanelEquipmentTree:
    """Tests for equipment tree functionality."""

    def test_populates_equipment_items(self, qapp):
        """Should populate tree with equipment items."""
        from gui_qt.widgets.pob_panel import PoBPanel

        items = {
            "Helmet": MockPoBItem(slot="Helmet", name="Test Helmet"),
            "Body Armour": MockPoBItem(slot="Body Armour", name="Test Armour"),
        }
        build = MockPoBBuild(items=items)
        profile = MockCharacterProfile(name="TestChar", build=build)
        profiles = {"TestChar": profile}
        manager = MockCharacterManager(profiles=profiles, active_profile=profile)
        panel = PoBPanel(manager)

        panel._on_profile_changed("TestChar")

        assert panel.equipment_tree.topLevelItemCount() == 2

    def test_clears_equipment_on_invalid_profile(self, qapp):
        """Should clear equipment when invalid profile selected."""
        from gui_qt.widgets.pob_panel import PoBPanel

        items = {"Helmet": MockPoBItem(slot="Helmet")}
        build = MockPoBBuild(items=items)
        profile = MockCharacterProfile(name="TestChar", build=build)
        profiles = {"TestChar": profile}
        manager = MockCharacterManager(profiles=profiles, active_profile=profile)
        panel = PoBPanel(manager)

        panel._on_profile_changed("TestChar")
        assert panel.equipment_tree.topLevelItemCount() > 0

        panel._on_profile_changed("(No profiles)")
        assert panel.equipment_tree.topLevelItemCount() == 0


class TestPoBPanelItemTextGeneration:
    """Tests for item text generation (PoE clipboard format)."""

    def test_generates_rarity_line(self, qapp):
        """Generated text should include rarity line."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(rarity="RARE", name="Test Item", base_type="Eternal Burgonet")

        text = panel._generate_item_text(item)

        assert "Rarity: Rare" in text

    def test_generates_name_and_base_type(self, qapp):
        """Generated text should include name and base type for rares."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(rarity="RARE", name="Doom Crown", base_type="Eternal Burgonet")

        text = panel._generate_item_text(item)

        assert "Doom Crown" in text
        assert "Eternal Burgonet" in text

    def test_generates_unique_format(self, qapp):
        """Generated text should handle unique items correctly."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(rarity="UNIQUE", name="Starforge", base_type="Infernal Sword")

        text = panel._generate_item_text(item)

        assert "Rarity: Unique" in text
        assert "Starforge" in text
        assert "Infernal Sword" in text

    def test_includes_item_level(self, qapp):
        """Generated text should include item level."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(item_level=86)

        text = panel._generate_item_text(item)

        assert "Item Level: 86" in text

    def test_includes_quality(self, qapp):
        """Generated text should include quality if present."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(quality=20)

        text = panel._generate_item_text(item)

        assert "Quality: +20%" in text

    def test_skips_zero_quality(self, qapp):
        """Generated text should skip quality if zero."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(quality=0)

        text = panel._generate_item_text(item)

        assert "Quality:" not in text

    def test_includes_sockets(self, qapp):
        """Generated text should include sockets."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(sockets="R-R-R-G-G-B")

        text = panel._generate_item_text(item)

        assert "Sockets: R-R-R-G-G-B" in text

    def test_includes_implicit_mods(self, qapp):
        """Generated text should include implicit mods."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(implicit_mods=["+50 to maximum Life"])

        text = panel._generate_item_text(item)

        assert "+50 to maximum Life" in text

    def test_includes_explicit_mods(self, qapp):
        """Generated text should include explicit mods."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(explicit_mods=[
            "+100 to maximum Life",
            "+40% to Fire Resistance",
        ])

        text = panel._generate_item_text(item)

        assert "+100 to maximum Life" in text
        assert "+40% to Fire Resistance" in text

    def test_filters_metadata_mods(self, qapp):
        """Generated text should filter out metadata lines from mods."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(explicit_mods=[
            "Armour: 500",
            "ArmourBasePercentile: 0.5",
            "+100 to maximum Life",  # This should be included
        ])

        text = panel._generate_item_text(item)

        assert "Armour: 500" not in text
        assert "ArmourBasePercentile" not in text
        assert "+100 to maximum Life" in text

    def test_handles_unique_id_in_base_type(self, qapp):
        """Should clean up base_type if it contains 'Unique ID:'."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(
            rarity="UNIQUE",
            name="Starforge",
            base_type="Unique ID: 12345"
        )

        text = panel._generate_item_text(item)

        assert "Unique ID" not in text

    def test_includes_influences(self, qapp):
        """Generated text should include influence markers."""
        from gui_qt.widgets.pob_panel import PoBPanel

        panel = PoBPanel(MockCharacterManager())
        item = MockPoBItem(influences=["Shaper", "Elder"])

        text = panel._generate_item_text(item)

        assert "Shaper Item" in text
        assert "Elder Item" in text


class TestPoBPanelSignals:
    """Tests for signal emission."""

    def test_emits_price_check_on_double_click(self, qapp):
        """Should emit price_check_requested on item double-click."""
        from gui_qt.widgets.pob_panel import PoBPanel

        items = {"Helmet": MockPoBItem(slot="Helmet", name="Test Helmet")}
        build = MockPoBBuild(items=items)
        profile = MockCharacterProfile(name="TestChar", build=build)
        profiles = {"TestChar": profile}
        manager = MockCharacterManager(profiles=profiles, active_profile=profile)
        panel = PoBPanel(manager)
        panel._on_profile_changed("TestChar")

        # Track signal emission
        signal_received = []
        panel.price_check_requested.connect(lambda text: signal_received.append(text))

        # Simulate double-click on first item
        item = panel.equipment_tree.topLevelItem(0)
        if item:
            panel._on_item_double_clicked(item, 0)

        assert len(signal_received) == 1
        assert "Rarity:" in signal_received[0]


class TestPoBPanelRefresh:
    """Tests for refresh functionality."""

    def test_refresh_reloads_profiles(self, qapp):
        """Refresh should reload profile list."""
        from gui_qt.widgets.pob_panel import PoBPanel

        manager = MockCharacterManager(profiles={})
        panel = PoBPanel(manager)
        assert panel.profile_combo.count() == 1  # "(No profiles)"

        # Add profiles and refresh
        manager._profiles = {"NewChar": MockCharacterProfile(name="NewChar")}
        panel.refresh()

        assert panel.profile_combo.count() == 1
        assert panel.profile_combo.itemText(0) == "NewChar"


class TestPoBPanelGetEquipment:
    """Tests for get_all_equipment method."""

    def test_returns_all_equipment(self, qapp):
        """Should return all equipment items with text."""
        from gui_qt.widgets.pob_panel import PoBPanel

        items = {
            "Helmet": MockPoBItem(slot="Helmet", name="Helm"),
            "Boots": MockPoBItem(slot="Boots", name="Boots"),
        }
        build = MockPoBBuild(items=items)
        profile = MockCharacterProfile(name="TestChar", build=build)
        profiles = {"TestChar": profile}
        manager = MockCharacterManager(profiles=profiles, active_profile=profile)
        panel = PoBPanel(manager)
        panel._on_profile_changed("TestChar")

        equipment = panel.get_all_equipment()

        assert len(equipment) == 2
        for item in equipment:
            assert "slot" in item
            assert "data" in item
            assert "text" in item
            assert "Rarity:" in item["text"]
