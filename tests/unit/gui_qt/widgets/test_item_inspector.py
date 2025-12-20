"""
Tests for the ItemInspectorWidget.

Tests mod display, breakdown logic, tier highlighting, and build-effective calculations.
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Optional, List

from PyQt6.QtWidgets import QApplication

from gui_qt.widgets.item_inspector import ItemInspectorWidget


@pytest.fixture
def qapp():
    """Create QApplication for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def item_inspector(qapp, qtbot):
    """Create an ItemInspectorWidget for testing."""
    widget = ItemInspectorWidget()
    qtbot.addWidget(widget)
    return widget


# Mock item classes for testing
@dataclass
class MockParsedItem:
    """Mock ParsedItem for testing."""
    name: str = "Test Item"
    base_type: str = "Gold Ring"
    rarity: str = "Rare"
    item_level: Optional[int] = 75
    required_level: Optional[int] = None
    implicits: List[str] = None
    explicits: List[str] = None
    corrupted: bool = False
    sockets: Optional[str] = None
    links: Optional[int] = None
    quality: Optional[int] = None
    stack_size: Optional[int] = None
    map_tier: Optional[int] = None
    gem_level: Optional[int] = None
    flavor_text: Optional[str] = None

    def __post_init__(self):
        if self.implicits is None:
            self.implicits = []
        if self.explicits is None:
            self.explicits = []


@dataclass
class MockBuildStats:
    """Mock BuildStats for testing."""
    total_life: float = 5000
    life_inc: float = 150.0  # 150% increased life
    total_es: float = 0
    es_inc: float = 0
    armour: float = 0
    armour_inc: float = 0
    # Resistance fields required by calculator
    fire_res: float = 75.0
    fire_overcap: float = 0.0
    cold_res: float = 75.0
    cold_overcap: float = 0.0
    lightning_res: float = 75.0
    lightning_overcap: float = 0.0
    chaos_res: float = 0.0
    chaos_overcap: float = 0.0


@dataclass
class MockDPSStats:
    """Mock DPSStats for testing."""
    total_dps: float = 100000
    main_damage_type: str = "physical"
    has_crit: bool = True
    has_elemental: bool = False


class TestItemInspectorInitialization:
    """Tests for ItemInspectorWidget initialization."""

    def test_default_initialization(self, item_inspector):
        """Test that widget initializes correctly."""
        assert item_inspector._browser is not None
        assert item_inspector._build_stats is None
        assert item_inspector._calculator is None
        assert item_inspector._archetype is None
        assert item_inspector._evaluation is None
        assert item_inspector._upgrade_calculator is None
        assert item_inspector._dps_calculator is None
        assert item_inspector._current_equipped_mods is None

    def test_minimum_height_set(self, item_inspector):
        """Test that minimum height is set."""
        assert item_inspector.minimumHeight() == 200

    def test_placeholder_shown_initially(self, item_inspector):
        """Test that placeholder is shown initially."""
        html = item_inspector._browser.toHtml()
        assert "No item selected" in html


class TestItemInspectorBuildStats:
    """Tests for build stats configuration."""

    def test_set_build_stats(self, item_inspector):
        """Test setting build stats."""
        stats = MockBuildStats()
        item_inspector.set_build_stats(stats)

        assert item_inspector._build_stats == stats
        assert item_inspector._calculator is not None
        assert item_inspector._upgrade_calculator is not None

    def test_set_build_stats_none(self, item_inspector):
        """Test clearing build stats."""
        # First set stats
        stats = MockBuildStats()
        item_inspector.set_build_stats(stats)

        # Then clear
        item_inspector.set_build_stats(None)

        assert item_inspector._build_stats is None
        assert item_inspector._calculator is None
        assert item_inspector._upgrade_calculator is None

    def test_set_archetype(self, item_inspector):
        """Test setting build archetype."""
        archetype = Mock()
        item_inspector.set_archetype(archetype)

        assert item_inspector._archetype == archetype

    def test_set_dps_stats(self, item_inspector):
        """Test setting DPS stats."""
        stats = MockDPSStats()
        item_inspector.set_dps_stats(stats)

        assert item_inspector._dps_stats == stats
        assert item_inspector._dps_calculator is not None

    def test_set_dps_stats_none(self, item_inspector):
        """Test clearing DPS stats."""
        stats = MockDPSStats()
        item_inspector.set_dps_stats(stats)

        item_inspector.set_dps_stats(None)

        assert item_inspector._dps_stats is None
        assert item_inspector._dps_calculator is None

    def test_set_evaluation(self, item_inspector):
        """Test setting evaluation results."""
        evaluation = Mock()
        item_inspector.set_evaluation(evaluation)

        assert item_inspector._evaluation == evaluation


class TestItemInspectorCurrentEquipped:
    """Tests for current equipped item comparison."""

    def test_set_current_equipped_with_mods(self, item_inspector):
        """Test setting current equipped item."""
        item = MockParsedItem(
            implicits=["+20 to maximum Life"],
            explicits=["+50 to Strength", "+30% Fire Resistance"]
        )
        item_inspector.set_current_equipped(item)

        assert item_inspector._current_equipped_mods is not None
        assert len(item_inspector._current_equipped_mods) == 3
        assert "+20 to maximum Life" in item_inspector._current_equipped_mods
        assert "+50 to Strength" in item_inspector._current_equipped_mods

    def test_set_current_equipped_with_mods_field(self, item_inspector):
        """Test setting current equipped with 'mods' field instead of explicits."""
        # Use Mock but make it list-friendly
        item = Mock()
        item.implicits = []
        item.explicits = []
        item.explicit_mods = []
        # The widget tries getattr with default [], so mock it properly

        # Actually, let's use a real object with the mods attribute
        from types import SimpleNamespace
        item = SimpleNamespace(
            implicits=[],
            explicits=None,
            explicit_mods=None,
            mods=["+30 to Intelligence"]
        )

        item_inspector.set_current_equipped(item)

        assert "+30 to Intelligence" in item_inspector._current_equipped_mods

    def test_set_current_equipped_none(self, item_inspector):
        """Test clearing current equipped item."""
        # First set an item
        item = MockParsedItem(explicits=["+50 to Strength"])
        item_inspector.set_current_equipped(item)

        # Then clear
        item_inspector.set_current_equipped(None)

        assert item_inspector._current_equipped_mods is None

    def test_clear_current_equipped(self, item_inspector):
        """Test clear_current_equipped method."""
        item = MockParsedItem(explicits=["+50 to Strength"])
        item_inspector.set_current_equipped(item)

        item_inspector.clear_current_equipped()

        assert item_inspector._current_equipped_mods is None


class TestItemInspectorItemDisplay:
    """Tests for item display functionality."""

    def test_set_item_none_shows_placeholder(self, item_inspector):
        """Test that setting None shows placeholder."""
        item_inspector.set_item(None)

        html = item_inspector._browser.toHtml()
        assert "No item selected" in html

    def test_clear_shows_placeholder(self, item_inspector):
        """Test that clear() shows placeholder."""
        item_inspector.clear()

        html = item_inspector._browser.toHtml()
        assert "No item selected" in html

    def test_set_item_displays_name(self, item_inspector):
        """Test that item name is displayed."""
        item = MockParsedItem(name="Crimson Ring", base_type="Gold Ring")
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Crimson Ring" in html

    def test_set_item_displays_rarity(self, item_inspector):
        """Test that rarity is displayed."""
        item = MockParsedItem(name="Test Item", rarity="Unique")
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Rarity: Unique" in html

    def test_set_item_displays_base_type(self, item_inspector):
        """Test that base type is displayed when different from name."""
        item = MockParsedItem(name="Rare Ring", base_type="Gold Ring")
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Gold Ring" in html

    def test_set_item_displays_item_level(self, item_inspector):
        """Test that item level is displayed."""
        item = MockParsedItem(item_level=86)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Item Level" in html
        assert "86" in html

    def test_set_item_displays_required_level(self, item_inspector):
        """Test that required level is displayed."""
        item = MockParsedItem(required_level=60)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Required Level" in html
        assert "60" in html

    def test_set_item_displays_sockets_and_links(self, item_inspector):
        """Test that sockets and links are displayed."""
        item = MockParsedItem(sockets="R-R-R-B-B-G", links=4)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Sockets" in html
        assert "R-R-R-B-B-G" in html
        assert "Links" in html
        assert "4" in html

    def test_set_item_displays_quality(self, item_inspector):
        """Test that quality is displayed."""
        item = MockParsedItem(quality=20)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Quality" in html
        assert "+20%" in html

    def test_set_item_displays_corrupted(self, item_inspector):
        """Test that corrupted status is displayed."""
        item = MockParsedItem(corrupted=True)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Corrupted" in html

    def test_set_item_displays_map_tier(self, item_inspector):
        """Test that map tier is displayed."""
        item = MockParsedItem(map_tier=16)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Map Tier" in html
        assert "16" in html

    def test_set_item_displays_gem_level(self, item_inspector):
        """Test that gem level is displayed."""
        item = MockParsedItem(gem_level=20)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Gem Level" in html
        assert "20" in html

    def test_set_item_displays_stack_size(self, item_inspector):
        """Test that stack size is displayed."""
        item = MockParsedItem(stack_size=40)
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Stack Size" in html
        assert "40" in html

    def test_set_item_displays_flavor_text(self, item_inspector):
        """Test that flavor text is displayed."""
        item = MockParsedItem(flavor_text="A ring of great power")
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "A ring of great power" in html


class TestItemInspectorModDisplay:
    """Tests for mod display (implicits and explicits)."""

    def test_set_item_displays_implicit_mods(self, item_inspector):
        """Test that implicit mods are displayed."""
        item = MockParsedItem(
            implicits=["+20 to maximum Life", "+15% to Fire Resistance"]
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Implicit:" in html
        assert "+20 to maximum Life" in html
        assert "+15% to Fire Resistance" in html

    def test_set_item_displays_explicit_mods(self, item_inspector):
        """Test that explicit mods are displayed."""
        item = MockParsedItem(
            explicits=[
                "+50 to Strength",
                "+30% Cold Resistance",
                "+80 to maximum Life"
            ]
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Explicit:" in html
        assert "+50 to Strength" in html
        assert "+30% Cold Resistance" in html
        assert "+80 to maximum Life" in html

    def test_set_item_no_implicits(self, item_inspector):
        """Test item display with no implicit mods."""
        item = MockParsedItem(
            implicits=[],
            explicits=["+50 to Strength"]
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Implicit:" not in html
        assert "Explicit:" in html

    def test_set_item_no_explicits(self, item_inspector):
        """Test item display with no explicit mods."""
        item = MockParsedItem(
            implicits=["+20 to maximum Life"],
            explicits=[]
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Implicit:" in html
        assert "Explicit:" not in html

    @patch('gui_qt.widgets.item_inspector.detect_mod_tier')
    def test_mod_tier_detection_called(self, mock_detect_tier, item_inspector):
        """Test that mod tier detection is called for each mod."""
        from core.mod_tier_detector import ModTierResult

        # Mock tier detection
        mock_detect_tier.return_value = ModTierResult(
            mod_text="+80 to maximum Life",
            stat_type="life",
            value=80,
            tier=1,
            is_crafted=False,
            is_implicit=False
        )

        item = MockParsedItem(
            implicits=["+20 to maximum Life"],
            explicits=["+80 to maximum Life", "+50 to Strength"]
        )
        item_inspector.set_item(item)

        # Should be called for each mod
        assert mock_detect_tier.call_count == 3

    @patch('gui_qt.widgets.item_inspector.detect_mod_tier')
    def test_tier_label_displayed(self, mock_detect_tier, item_inspector):
        """Test that tier labels are displayed."""
        from core.mod_tier_detector import ModTierResult

        # Mock T1 tier
        mock_detect_tier.return_value = ModTierResult(
            mod_text="+80 to maximum Life",
            stat_type="life",
            value=80,
            tier=1,
            is_crafted=False,
            is_implicit=False
        )

        item = MockParsedItem(
            explicits=["+80 to maximum Life"]
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "[T1]" in html

    @patch('gui_qt.widgets.item_inspector.detect_mod_tier')
    def test_crafted_mod_color(self, mock_detect_tier, item_inspector):
        """Test that crafted mods use different color."""
        from core.mod_tier_detector import ModTierResult

        # Mock crafted mod
        mock_detect_tier.return_value = ModTierResult(
            mod_text="(crafted) +30% Fire Resistance",
            stat_type="fire_resistance",
            value=30,
            tier=None,
            is_crafted=True,
            is_implicit=False
        )

        item = MockParsedItem(
            explicits=["(crafted) +30% Fire Resistance"]
        )
        item_inspector.set_item(item)

        # Should render without errors (color handled internally)
        html = item_inspector._browser.toHtml()
        assert "(crafted) +30% Fire Resistance" in html


class TestItemInspectorEffectiveValues:
    """Tests for build-effective values display."""

    def test_effective_values_not_shown_without_calculator(self, item_inspector):
        """Test that effective values aren't shown without build stats."""
        item = MockParsedItem(
            explicits=["+80 to maximum Life"]
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Build-Effective Values" not in html

    @patch('core.build_stat_calculator.BuildStatCalculator.calculate_effective_values')
    def test_effective_values_shown_with_calculator(self, mock_calc, item_inspector):
        """Test that effective values are shown with build stats."""
        from core.build_stat_calculator import EffectiveModValue

        # Setup build stats
        stats = MockBuildStats(total_life=5000, life_inc=150.0)
        item_inspector.set_build_stats(stats)

        # Mock calculation result
        mock_calc.return_value = [
            EffectiveModValue(
                mod_text="+80 to maximum Life",
                mod_type="life",
                raw_value=80,
                effective_value=200,
                multiplier=2.5,
                explanation="+80 life → 200 effective"
            )
        ]

        item = MockParsedItem(
            explicits=["+80 to maximum Life"]
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Build-Effective Values" in html
        assert "effective" in html.lower()

    @patch('core.build_stat_calculator.BuildStatCalculator.calculate_effective_values')
    def test_effective_values_build_summary(self, mock_calc, item_inspector):
        """Test that build summary is shown with effective values."""
        from core.build_stat_calculator import EffectiveModValue

        # Return at least one result so the section is shown
        mock_calc.return_value = [
            EffectiveModValue(
                mod_text="+80 to maximum Life",
                mod_type="life",
                raw_value=80,
                effective_value=240,
                multiplier=3.0,
                explanation="+80 life → 240 effective"
            )
        ]

        stats = MockBuildStats(total_life=6500, life_inc=200.0)
        item_inspector.set_build_stats(stats)

        item = MockParsedItem(explicits=["+80 to maximum Life"])
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        # Should show life total and/or % inc in the build summary
        assert "6500" in html or "200" in html


class TestItemInspectorUpgradeComparison:
    """Tests for upgrade comparison display."""

    @patch('core.upgrade_calculator.UpgradeCalculator.compare_items')
    def test_upgrade_comparison_shown(self, mock_compare, item_inspector):
        """Test that upgrade comparison is shown."""
        # Setup
        stats = MockBuildStats()
        item_inspector.set_build_stats(stats)
        item_inspector.set_current_equipped(
            MockParsedItem(explicits=["+50 to Strength"])
        )

        # Mock comparison result
        mock_compare.return_value = {
            "impact": Mock(),
            "is_upgrade": True,
            "is_downgrade": False,
            "summary": "Significant upgrade",
            "improvements": ["+30 to maximum Life"],
            "losses": [],
            "gaps": Mock(has_gaps=lambda: False)
        }

        item = MockParsedItem(explicits=["+80 to maximum Life"])
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "UPGRADE" in html or "upgrade" in html.lower()

    @patch('core.upgrade_calculator.UpgradeCalculator.compare_items')
    def test_downgrade_shown(self, mock_compare, item_inspector):
        """Test that downgrades are indicated."""
        stats = MockBuildStats()
        item_inspector.set_build_stats(stats)
        item_inspector.set_current_equipped(
            MockParsedItem(explicits=["+80 to maximum Life"])
        )

        mock_compare.return_value = {
            "impact": Mock(),
            "is_upgrade": False,
            "is_downgrade": True,
            "summary": "Downgrade",
            "improvements": [],
            "losses": ["-30 to maximum Life"],
            "gaps": Mock(has_gaps=lambda: False)
        }

        item = MockParsedItem(explicits=["+50 to maximum Life"])
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "DOWNGRADE" in html or "downgrade" in html.lower()


class TestItemInspectorDPSImpact:
    """Tests for DPS impact display."""

    @patch('core.dps_impact_calculator.DPSImpactCalculator.calculate_impact')
    def test_dps_impact_shown(self, mock_calc, item_inspector):
        """Test that DPS impact is shown."""
        from core.dps_impact_calculator import DPSImpactResult, DPSModImpact

        # Setup
        stats = MockDPSStats()
        item_inspector.set_dps_stats(stats)

        # Mock result
        mock_calc.return_value = DPSImpactResult(
            total_dps_percent=15.0,
            summary="Significant DPS increase",
            build_info="Physical DPS: 100k",
            mod_impacts=[
                DPSModImpact(
                    mod_text="+30% Physical Damage",
                    mod_category="damage",
                    raw_value=30.0,
                    estimated_dps_change=15000,
                    estimated_dps_percent=15.0,
                    relevance="high",
                    explanation="+30% physical damage"
                )
            ]
        )

        item = MockParsedItem(explicits=["+30% Physical Damage"])
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "DPS Impact" in html

    @patch('core.dps_impact_calculator.DPSImpactCalculator.calculate_impact')
    def test_dps_impact_not_shown_without_mods(self, mock_calc, item_inspector):
        """Test that DPS impact isn't shown if no offensive mods."""
        from core.dps_impact_calculator import DPSImpactResult

        stats = MockDPSStats()
        item_inspector.set_dps_stats(stats)

        # Mock result with no mod impacts
        mock_calc.return_value = DPSImpactResult(
            total_dps_percent=0,
            summary="",
            build_info="",
            mod_impacts=[]
        )

        item = MockParsedItem(explicits=["+50 to Strength"])
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "DPS Impact" not in html


class TestItemInspectorArchetypeScores:
    """Tests for archetype-weighted scores display."""

    def test_archetype_scores_shown(self, item_inspector):
        """Test that archetype scores are shown."""
        # Mock evaluation with archetype details
        evaluation = Mock()
        evaluation.archetype_affix_details = [
            {
                "affix_type": "life",
                "multiplier": 1.5,
                "base_weight": 10,
                "weighted_weight": 15,
                "tier": "T1"
            }
        ]
        evaluation.total_score = 50
        evaluation.archetype_weighted_score = 65
        evaluation.build_archetype = Mock()
        evaluation.build_archetype.get_summary = lambda: "Life-based melee"

        item_inspector.set_evaluation(evaluation)

        item = MockParsedItem(explicits=["+80 to maximum Life"])
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Archetype-Weighted Scores" in html

    def test_archetype_scores_not_shown_without_evaluation(self, item_inspector):
        """Test that archetype scores aren't shown without evaluation."""
        item = MockParsedItem(explicits=["+80 to maximum Life"])
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "Archetype-Weighted Scores" not in html


class TestItemInspectorHTMLSafety:
    """Tests for HTML/XSS safety."""

    def test_html_escaping_in_name(self, item_inspector):
        """Test that HTML in item name is escaped."""
        item = MockParsedItem(name="<script>alert('xss')</script>")
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        # Should be escaped
        assert "<script>" not in html
        assert "&lt;script&gt;" in html or "alert" not in html

    def test_html_escaping_in_base_type(self, item_inspector):
        """Test that HTML in base type is escaped."""
        item = MockParsedItem(
            name="Safe Name",
            base_type="<img src=x onerror=alert('xss')>"
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()
        assert "<img" not in html or "&lt;img" in html


class TestItemInspectorCompleteWorkflow:
    """Integration tests for complete workflows."""

    def test_complete_rare_item_with_all_features(self, item_inspector):
        """Test displaying a complete rare item with all features."""
        # Setup all features
        stats = MockBuildStats(total_life=6000, life_inc=180.0)
        item_inspector.set_build_stats(stats)

        item = MockParsedItem(
            name="Crimson Loop",
            base_type="Gold Ring",
            rarity="Rare",
            item_level=86,
            required_level=60,
            implicits=["+20 to maximum Life"],
            explicits=[
                "+80 to maximum Life",
                "+50 to Strength",
                "+30% Fire Resistance",
                "+25% Cold Resistance"
            ],
            corrupted=False
        )
        item_inspector.set_item(item)

        html = item_inspector._browser.toHtml()

        # Verify all sections
        assert "Crimson Loop" in html
        assert "Rare" in html
        assert "Item Level" in html
        assert "86" in html
        assert "Implicit:" in html
        assert "Explicit:" in html
        assert "+80 to maximum Life" in html
        assert "+50 to Strength" in html

    def test_switching_between_items(self, item_inspector):
        """Test switching between different items."""
        item1 = MockParsedItem(name="First Item", rarity="Rare")
        item2 = MockParsedItem(name="Second Item", rarity="Unique")

        # Show first item
        item_inspector.set_item(item1)
        html1 = item_inspector._browser.toHtml()
        assert "First Item" in html1
        assert "Second Item" not in html1

        # Switch to second item
        item_inspector.set_item(item2)
        html2 = item_inspector._browser.toHtml()
        assert "Second Item" in html2
        assert "First Item" not in html2

    def test_clear_after_displaying_item(self, item_inspector):
        """Test clearing after displaying an item."""
        item = MockParsedItem(name="Test Item")
        item_inspector.set_item(item)

        # Verify item is shown
        html = item_inspector._browser.toHtml()
        assert "Test Item" in html

        # Clear
        item_inspector.clear()

        # Should show placeholder
        html = item_inspector._browser.toHtml()
        assert "No item selected" in html
        assert "Test Item" not in html
