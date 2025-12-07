"""Tests for AIUpgradeAdvisorService."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from core.ai_upgrade_advisor import (
    AIUpgradeAdvisorService,
    StashUpgradeCandidate,
    TradeSearchSuggestion,
    UpgradeRecommendation,
    SlotUpgradeAnalysis,
    BuildResearch,
    UpgradeAdvisorResult,
    UpgradeTier,
    get_ai_upgrade_advisor,
    reset_ai_upgrade_advisor,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create mock database."""
    db = MagicMock()
    return db


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = MagicMock()
    config.league = "Settlers"
    config.data = {"stash": {"account_name": "TestAccount"}}
    return config


@pytest.fixture
def advisor(mock_db, mock_config):
    """Create advisor instance."""
    reset_ai_upgrade_advisor()
    return AIUpgradeAdvisorService(mock_db, mock_config)


@pytest.fixture
def mock_pob_item():
    """Create mock PoB item."""
    item = MagicMock()
    item.slot = "Helmet"
    item.rarity = "RARE"
    item.name = "Test Helmet"
    item.base_type = "Royal Burgonet"
    item.item_level = 85
    item.sockets = "R-R-R-G"
    item.implicit_mods = ["+30 to Maximum Life"]
    item.explicit_mods = [
        "+80 to Maximum Life",
        "+40% to Fire Resistance",
        "+35% to Cold Resistance",
    ]
    item.display_name = "Test Helmet (Royal Burgonet)"
    return item


@pytest.fixture
def mock_profile(mock_pob_item):
    """Create mock character profile."""
    profile = MagicMock()
    profile.name = "Test Character"
    profile.build = MagicMock()
    profile.build.class_name = "Marauder"
    profile.build.ascendancy = "Juggernaut"
    profile.build.level = 90
    profile.build.main_skill = "Cyclone"
    profile.build.items = {
        "Helmet": mock_pob_item,
        "Body Armour": None,  # Empty slot
    }
    profile.build.stats = {
        "Life": 5000,
        "EnergyShield": 0,
        "FireResist": 75,
        "ColdResist": 60,
        "LightningResist": 75,
        "ChaosResist": -20,
    }
    profile.build.skills = ["Cyclone", "Blood and Sand"]
    return profile


@pytest.fixture
def mock_priced_item():
    """Create mock priced item from stash."""
    item = MagicMock()
    item.name = "Siege Dome"
    item.type_line = "Siege Dome"
    item.base_type = "Eternal Burgonet"
    item.item_class = "Helmet"
    item.stack_size = 1
    item.ilvl = 86
    item.rarity = "Rare"
    item.identified = True
    item.corrupted = False
    item.links = 4
    item.sockets = "R-R-R-G"
    item.x = 0
    item.y = 0
    item.total_price = 50.0
    item.raw_item = {
        "implicitMods": ["+35 to Maximum Life"],
        "explicitMods": [
            "+95 to Maximum Life",
            "+45% to Fire Resistance",
            "+40% to Cold Resistance",
            "+38% to Lightning Resistance",
        ],
    }
    return item


# =============================================================================
# StashUpgradeCandidate Tests
# =============================================================================


class TestStashUpgradeCandidate:
    """Tests for StashUpgradeCandidate dataclass."""

    def test_all_mods_combines_implicits_and_explicits(self):
        """all_mods returns both implicit and explicit mods."""
        candidate = StashUpgradeCandidate(
            name="Test Item",
            base_type="Test Base",
            item_class="Helmet",
            tab_name="Tab 1",
            tab_index=0,
            position=(0, 0),
            rarity="Rare",
            item_level=85,
            links=4,
            sockets="R-R-R-G",
            corrupted=False,
            implicit_mods=["+30 to Life"],
            explicit_mods=["+50 to Life", "+40% Fire Res"],
        )

        assert len(candidate.all_mods) == 3
        assert "+30 to Life" in candidate.all_mods
        assert "+50 to Life" in candidate.all_mods

    def test_to_item_text_format(self):
        """to_item_text returns proper PoE item format."""
        candidate = StashUpgradeCandidate(
            name="Siege Dome",
            base_type="Eternal Burgonet",
            item_class="Helmet",
            tab_name="Tab 1",
            tab_index=0,
            position=(0, 0),
            rarity="Rare",
            item_level=86,
            links=4,
            sockets="R-R-R-G",
            corrupted=False,
            implicit_mods=["+30 to Life"],
            explicit_mods=["+80 to Life"],
        )

        text = candidate.to_item_text()

        assert "Rarity: Rare" in text
        assert "Siege Dome" in text
        assert "Eternal Burgonet" in text
        assert "Item Level: 86" in text
        assert "+30 to Life" in text
        assert "+80 to Life" in text

    def test_corrupted_item_shows_corruption(self):
        """Corrupted items show corruption tag."""
        candidate = StashUpgradeCandidate(
            name="Test",
            base_type="Test Base",
            item_class="Helmet",
            tab_name="Tab 1",
            tab_index=0,
            position=(0, 0),
            rarity="Rare",
            item_level=85,
            links=0,
            sockets="",
            corrupted=True,
        )

        text = candidate.to_item_text()
        assert "Corrupted" in text


# =============================================================================
# TradeSearchSuggestion Tests
# =============================================================================


class TestTradeSearchSuggestion:
    """Tests for TradeSearchSuggestion dataclass."""

    def test_to_search_description(self):
        """to_search_description formats properly."""
        suggestion = TradeSearchSuggestion(
            slot="Helmet",
            description="Defensive upgrade",
            required_stats=[
                {"name": "Maximum Life", "min": 70},
                {"name": "Fire Resistance", "min": 30},
            ],
            max_price_chaos=100,
            priority=1,
        )

        desc = suggestion.to_search_description()

        assert "Helmet" in desc
        assert "Maximum Life" in desc
        assert "70" in desc
        assert "Fire Resistance" in desc
        assert "100c" in desc


# =============================================================================
# BuildResearch Tests
# =============================================================================


class TestBuildResearch:
    """Tests for BuildResearch dataclass."""

    def test_to_context_string(self):
        """to_context_string includes all relevant info."""
        research = BuildResearch(
            build_name="Cyclone Juggernaut",
            key_uniques=["Atziri's Disfavour", "Kaom's Heart"],
            stat_priorities=["Life", "Physical Damage", "Attack Speed"],
            playstyle_notes="Spin to win melee build",
            budget_tiers={"starter": "5div", "endgame": "50div"},
        )

        context = research.to_context_string()

        assert "Cyclone Juggernaut" in context
        assert "Atziri's Disfavour" in context
        assert "Life" in context
        assert "Spin to win" in context
        assert "5div" in context


# =============================================================================
# AIUpgradeAdvisorService Tests
# =============================================================================


class TestAIUpgradeAdvisorServiceInit:
    """Tests for service initialization."""

    def test_init_stores_db(self, mock_db, mock_config):
        """Service stores database reference."""
        advisor = AIUpgradeAdvisorService(mock_db, mock_config)
        assert advisor._db is mock_db

    def test_init_stores_config(self, mock_db, mock_config):
        """Service stores config reference."""
        advisor = AIUpgradeAdvisorService(mock_db, mock_config)
        assert advisor._config is mock_config

    def test_init_empty_research_cache(self, mock_db, mock_config):
        """Service starts with empty research cache."""
        advisor = AIUpgradeAdvisorService(mock_db, mock_config)
        assert len(advisor._build_research_cache) == 0


class TestAIUpgradeAdvisorStashScanning:
    """Tests for stash candidate scanning."""

    def test_get_stash_candidates_no_snapshot(self, advisor):
        """Returns empty list when no stash snapshot exists."""
        with patch.object(advisor, 'get_stash_storage') as mock_storage_fn:
            mock_storage = MagicMock()
            mock_storage.load_latest_snapshot.return_value = None
            mock_storage_fn.return_value = mock_storage

            candidates = advisor.get_stash_candidates_for_slot(
                slot="Helmet",
                account_name="TestAccount",
                league="Settlers",
            )

            assert candidates == []

    def test_get_stash_candidates_filters_by_slot(self, advisor, mock_priced_item):
        """Only returns items matching the requested slot."""
        with patch.object(advisor, 'get_stash_storage') as mock_storage_fn:
            mock_storage = MagicMock()
            mock_snapshot = MagicMock()
            mock_valuation = MagicMock()

            # Create helmet item
            helmet = MagicMock()
            helmet.item_class = "Helmet"
            helmet.base_type = "Eternal Burgonet"
            helmet.name = "Test Helmet"
            helmet.type_line = "Eternal Burgonet"
            helmet.rarity = "Rare"
            helmet.ilvl = 85
            helmet.links = 4
            helmet.sockets = "R-R-R-G"
            helmet.corrupted = False
            helmet.total_price = 50.0
            helmet.x = 0
            helmet.y = 0
            helmet.raw_item = {"implicitMods": [], "explicitMods": []}

            # Create non-helmet item
            boots = MagicMock()
            boots.item_class = "Boots"
            boots.base_type = "Titan Greaves"
            boots.name = "Test Boots"

            mock_tab = MagicMock()
            mock_tab.name = "Gear Tab"
            mock_tab.index = 0
            mock_tab.items = [helmet, boots]

            mock_valuation.tabs = [mock_tab]

            mock_storage.load_latest_snapshot.return_value = mock_snapshot
            mock_storage.reconstruct_valuation.return_value = mock_valuation
            mock_storage_fn.return_value = mock_storage

            candidates = advisor.get_stash_candidates_for_slot(
                slot="Helmet",
                account_name="TestAccount",
                league="Settlers",
            )

            # Should only return the helmet
            assert len(candidates) == 1
            assert candidates[0].base_type == "Eternal Burgonet"


class TestAIUpgradeAdvisorTradeGeneration:
    """Tests for trade search suggestion generation."""

    def test_generate_trade_suggestions_adds_life(self, advisor, mock_profile):
        """Generates life requirement for life-based builds."""
        suggestions = advisor.generate_trade_suggestions(
            profile=mock_profile,
            slot="Helmet",
            budget_chaos=500,
        )

        # Should have at least one suggestion
        assert len(suggestions) >= 1

        # Find the defensive suggestion
        defensive = suggestions[0]
        stat_names = [s.get("name", "") for s in defensive.required_stats]

        # Should include life for life-based build
        assert any("Life" in name for name in stat_names)

    def test_generate_trade_suggestions_adds_missing_res(self, advisor, mock_profile):
        """Generates resistance requirements for uncapped resistances."""
        # Mock profile has cold res at 60 (uncapped) and chaos at -20
        suggestions = advisor.generate_trade_suggestions(
            profile=mock_profile,
            slot="Helmet",
            budget_chaos=500,
        )

        # Check that cold res is requested (it's at 60, below 75 cap)
        all_stats = []
        for sugg in suggestions:
            all_stats.extend(sugg.required_stats)

        stat_names = [s.get("name", "") for s in all_stats]
        assert any("Cold" in name for name in stat_names)


class TestAIUpgradeAdvisorContextBuilding:
    """Tests for context string building."""

    def test_build_upgrade_context_includes_build_info(self, advisor, mock_profile):
        """Context includes build summary."""
        context = advisor.build_upgrade_context(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
        )

        assert "BUILD CONTEXT" in context
        assert "Juggernaut" in context or "Marauder" in context

    def test_build_upgrade_context_includes_current_item(self, advisor, mock_profile):
        """Context includes current equipped item."""
        context = advisor.build_upgrade_context(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
        )

        assert "CURRENT HELMET" in context
        assert "Test Helmet" in context or "Royal Burgonet" in context

    def test_build_upgrade_context_shows_empty_slot(self, advisor, mock_profile):
        """Context shows empty slot indication."""
        context = advisor.build_upgrade_context(
            profile=mock_profile,
            slot="Body Armour",  # This is empty in mock
            stash_candidates=[],
        )

        assert "CURRENT BODY ARMOUR" in context
        assert "(Empty slot)" in context

    def test_build_upgrade_context_includes_stash_candidates(self, advisor, mock_profile):
        """Context includes stash candidate details."""
        candidate = StashUpgradeCandidate(
            name="Upgrade Helmet",
            base_type="Eternal Burgonet",
            item_class="Helmet",
            tab_name="Gear Tab",
            tab_index=0,
            position=(0, 0),
            rarity="Rare",
            item_level=86,
            links=4,
            sockets="R-R-R-G",
            corrupted=False,
            implicit_mods=[],
            explicit_mods=["+100 to Maximum Life"],
            chaos_value=75.0,
        )

        context = advisor.build_upgrade_context(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[candidate],
            include_stash=True,  # Must be True to include stash section
        )

        assert "STASH OPTIONS" in context
        assert "Upgrade Helmet" in context
        assert "Gear Tab" in context
        assert "+100 to Maximum Life" in context

    def test_build_upgrade_context_includes_research(self, advisor, mock_profile):
        """Context includes build research if provided."""
        research = BuildResearch(
            build_name="Cyclone Jugg",
            key_uniques=["Atziri's Disfavour"],
            stat_priorities=["Life", "Physical Damage"],
        )

        context = advisor.build_upgrade_context(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
            build_research=research,
        )

        assert "BUILD RESEARCH" in context
        assert "Atziri's Disfavour" in context


class TestAIUpgradeAdvisorPromptGeneration:
    """Tests for AI prompt generation."""

    def test_get_upgrade_prompt_includes_task_with_stash(self, advisor, mock_profile):
        """Prompt includes stash-focused task when include_stash=True."""
        prompt = advisor.get_upgrade_prompt(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
            trade_suggestions=[],
            include_stash=True,
        )

        assert "TASK" in prompt
        assert "BEST" in prompt
        assert "BETTER" in prompt
        assert "GOOD" in prompt
        assert "TRADE RECOMMENDATIONS" in prompt

    def test_get_upgrade_prompt_includes_task_trade_only(self, advisor, mock_profile):
        """Prompt includes trade-focused task when include_stash=False."""
        prompt = advisor.get_upgrade_prompt(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
            trade_suggestions=[],
            include_stash=False,
        )

        assert "TASK" in prompt
        assert "CURRENT ITEM ANALYSIS" in prompt
        assert "TRADE RECOMMENDATIONS" in prompt
        assert "PRIORITY STATS" in prompt
        assert "Budget" in prompt

    def test_get_upgrade_prompt_mentions_build(self, advisor, mock_profile):
        """Prompt mentions the specific build type."""
        prompt = advisor.get_upgrade_prompt(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
            trade_suggestions=[],
        )

        # Should mention ascendancy and main skill
        assert "Juggernaut" in prompt or "Marauder" in prompt
        assert "Cyclone" in prompt

    def test_get_upgrade_prompt_includes_game_version(self, mock_db, mock_profile):
        """Prompt includes game version context."""
        from core.game_version import GameVersion

        # Test PoE1
        mock_config_poe1 = MagicMock()
        mock_config_poe1.current_game = GameVersion.POE1
        mock_config_poe1.league = "Settlers"
        advisor1 = AIUpgradeAdvisorService(mock_db, mock_config_poe1)

        prompt1 = advisor1.get_upgrade_prompt(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
            trade_suggestions=[],
        )

        assert "Path of Exile 1" in prompt1
        assert "POE 1 ECONOMY" in prompt1 or "PATH OF EXILE 1 ECONOMY" in prompt1
        assert "Settlers" in prompt1

    def test_get_upgrade_prompt_poe2_economy_context(self, mock_db, mock_profile):
        """PoE2 prompt has correct economy context."""
        from core.game_version import GameVersion

        mock_config_poe2 = MagicMock()
        mock_config_poe2.current_game = GameVersion.POE2
        mock_config_poe2.league = "Dawn"
        advisor2 = AIUpgradeAdvisorService(mock_db, mock_config_poe2)

        prompt2 = advisor2.get_upgrade_prompt(
            profile=mock_profile,
            slot="Helmet",
            stash_candidates=[],
            trade_suggestions=[],
        )

        assert "Path of Exile 2" in prompt2
        assert "POE 2 ECONOMY" in prompt2 or "PATH OF EXILE 2 ECONOMY" in prompt2
        assert "Dawn" in prompt2
        # PoE2 should NOT mention Mirror of Kalandra
        assert "Do NOT reference Mirror" in prompt2 or "not in PoE2" in prompt2


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_get_ai_upgrade_advisor_creates_instance(self, mock_db, mock_config):
        """Factory creates advisor instance."""
        reset_ai_upgrade_advisor()
        advisor = get_ai_upgrade_advisor(mock_db, mock_config)
        assert isinstance(advisor, AIUpgradeAdvisorService)

    def test_get_ai_upgrade_advisor_returns_singleton(self, mock_db, mock_config):
        """Factory returns same instance on repeated calls."""
        reset_ai_upgrade_advisor()
        advisor1 = get_ai_upgrade_advisor(mock_db, mock_config)
        advisor2 = get_ai_upgrade_advisor(mock_db, mock_config)
        assert advisor1 is advisor2

    def test_reset_clears_singleton(self, mock_db, mock_config):
        """reset_ai_upgrade_advisor clears the singleton."""
        reset_ai_upgrade_advisor()
        advisor1 = get_ai_upgrade_advisor(mock_db, mock_config)
        reset_ai_upgrade_advisor()
        advisor2 = get_ai_upgrade_advisor(mock_db, mock_config)
        # After reset, should be different instances
        assert advisor1 is not advisor2


# =============================================================================
# UpgradeTier Tests
# =============================================================================


class TestUpgradeTier:
    """Tests for UpgradeTier enum."""

    def test_tier_values(self):
        """Enum has expected values."""
        assert UpgradeTier.BEST.value == "best"
        assert UpgradeTier.BETTER.value == "better"
        assert UpgradeTier.GOOD.value == "good"
        assert UpgradeTier.SIDEGRADE.value == "sidegrade"
        assert UpgradeTier.SKIP.value == "skip"


# =============================================================================
# UpgradeRecommendation Tests
# =============================================================================


class TestUpgradeRecommendation:
    """Tests for UpgradeRecommendation dataclass."""

    def test_source_from_stash(self):
        """Source shows stash tab for stash items."""
        candidate = StashUpgradeCandidate(
            name="Test",
            base_type="Test",
            item_class="Helmet",
            tab_name="Gear Tab",
            tab_index=0,
            position=(0, 0),
            rarity="Rare",
            item_level=85,
            links=0,
            sockets="",
            corrupted=False,
        )

        rec = UpgradeRecommendation(
            tier=UpgradeTier.BETTER,
            item=candidate,
            trade_suggestion=None,
            reason="Good stats",
        )

        assert "Stash: Gear Tab" in rec.source

    def test_source_from_trade(self):
        """Source shows trade search for trade suggestions."""
        suggestion = TradeSearchSuggestion(
            slot="Helmet",
            description="Test",
            required_stats=[],
            max_price_chaos=100,
            priority=1,
        )

        rec = UpgradeRecommendation(
            tier=UpgradeTier.BETTER,
            item=None,
            trade_suggestion=suggestion,
            reason="Better available on trade",
        )

        assert rec.source == "Trade Search"


# =============================================================================
# SlotUpgradeAnalysis Tests
# =============================================================================


class TestSlotUpgradeAnalysis:
    """Tests for SlotUpgradeAnalysis dataclass."""

    def test_has_stash_upgrades_true(self):
        """has_stash_upgrades returns True when stash items found."""
        candidate = StashUpgradeCandidate(
            name="Test",
            base_type="Test",
            item_class="Helmet",
            tab_name="Tab",
            tab_index=0,
            position=(0, 0),
            rarity="Rare",
            item_level=85,
            links=0,
            sockets="",
            corrupted=False,
        )

        rec = UpgradeRecommendation(
            tier=UpgradeTier.BEST,
            item=candidate,
            trade_suggestion=None,
            reason="Test",
        )

        analysis = SlotUpgradeAnalysis(
            slot="Helmet",
            current_item=None,
            best=rec,
        )

        assert analysis.has_stash_upgrades is True

    def test_has_stash_upgrades_false_when_only_trade(self):
        """has_stash_upgrades returns False when only trade suggestions."""
        suggestion = TradeSearchSuggestion(
            slot="Helmet",
            description="Test",
            required_stats=[],
            max_price_chaos=100,
            priority=1,
        )

        rec = UpgradeRecommendation(
            tier=UpgradeTier.BEST,
            item=None,
            trade_suggestion=suggestion,
            reason="Test",
        )

        analysis = SlotUpgradeAnalysis(
            slot="Helmet",
            current_item=None,
            best=rec,
        )

        assert analysis.has_stash_upgrades is False
