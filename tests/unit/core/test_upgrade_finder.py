"""
Tests for the Upgrade Finder Service.
"""
import pytest
from unittest.mock import Mock, patch

from core.upgrade_finder import (
    UpgradeFinderService,
    UpgradeFinderResult,
    UpgradeCandidate,
    SlotUpgradeResult,
    BIS_TO_POB_SLOT,
)
from core.pob_integration import CharacterProfile, PoBBuild, PoBItem
from core.build_stat_calculator import BuildStats


@pytest.fixture
def mock_character_manager():
    """Create a mock character manager."""
    manager = Mock()
    return manager


@pytest.fixture
def sample_build_stats():
    """Sample PoB stats for testing."""
    return {
        "Spec:LifeInc": 150.0,
        "Life": 5000.0,
        "Spec:EnergyShieldInc": 20.0,
        "EnergyShield": 100.0,
        "FireResist": 75.0,
        "FireResistOverCap": 20.0,
        "ColdResist": 75.0,
        "ColdResistOverCap": 10.0,
        "LightningResist": 75.0,
        "LightningResistOverCap": 5.0,
        "ChaosResist": 30.0,
        "Str": 200.0,
        "Dex": 100.0,
        "Int": 80.0,
        "CombinedDPS": 500000.0,
    }


@pytest.fixture
def sample_profile(sample_build_stats):
    """Create a sample character profile."""
    build = PoBBuild(
        class_name="Marauder",
        ascendancy="Juggernaut",
        level=95,
        stats=sample_build_stats,
        items={
            "Helmet": PoBItem(
                slot="Helmet",
                rarity="RARE",
                name="Golem Crown",
                base_type="Royal Burgonet",
                explicit_mods=[
                    "+80 to maximum Life",
                    "+30% to Fire Resistance",
                    "+25% to Cold Resistance",
                ],
            ),
            "Body Armour": PoBItem(
                slot="Body Armour",
                rarity="UNIQUE",
                name="Kaom's Heart",
                base_type="Glorious Plate",
                explicit_mods=[
                    "+500 to maximum Life",
                ],
            ),
        },
    )
    return CharacterProfile(
        name="TestCharacter",
        build=build,
        pob_code="test_code",
    )


class TestUpgradeCandidate:
    """Tests for UpgradeCandidate dataclass."""

    def test_all_mods_combines_implicit_and_explicit(self):
        """Test that all_mods returns both implicit and explicit mods."""
        candidate = UpgradeCandidate(
            name="Test Helm",
            base_type="Royal Burgonet",
            item_level=84,
            implicit_mods=["+1 to Maximum Power Charges"],
            explicit_mods=["+90 to maximum Life", "+40% to Fire Resistance"],
        )

        assert len(candidate.all_mods) == 3
        assert "+1 to Maximum Power Charges" in candidate.all_mods
        assert "+90 to maximum Life" in candidate.all_mods

    def test_get_summary_with_impact(self):
        """Test summary generation with upgrade impact."""
        from core.upgrade_calculator import UpgradeImpact

        candidate = UpgradeCandidate(
            name="Better Helm",
            base_type="Royal Burgonet",
            item_level=84,
            upgrade_impact=UpgradeImpact(
                effective_life_delta=150.0,
                fire_res_delta=10.0,
                cold_res_delta=5.0,
            ),
            dps_percent_change=2.5,
        )

        summary = candidate.get_summary()
        assert "+150 life" in summary
        assert "+15% res" in summary
        assert "+2.5% DPS" in summary

    def test_get_summary_empty(self):
        """Test summary with no improvements."""
        candidate = UpgradeCandidate(
            name="Sidegrade Helm",
            base_type="Royal Burgonet",
            item_level=84,
        )

        assert candidate.get_summary() == "Minor improvement"


class TestSlotUpgradeResult:
    """Tests for SlotUpgradeResult dataclass."""

    def test_has_upgrades_true(self):
        """Test has_upgrades returns True when candidates exist."""
        result = SlotUpgradeResult(
            slot="Helmet",
            current_item=None,
            candidates=[
                UpgradeCandidate(name="Helm 1", base_type="Burgonet", item_level=80),
            ],
        )
        assert result.has_upgrades is True

    def test_has_upgrades_false(self):
        """Test has_upgrades returns False when no candidates."""
        result = SlotUpgradeResult(
            slot="Helmet",
            current_item=None,
            candidates=[],
        )
        assert result.has_upgrades is False

    def test_best_upgrade_returns_first(self):
        """Test best_upgrade returns the first candidate."""
        candidates = [
            UpgradeCandidate(name="Best", base_type="Burgonet", item_level=86, total_score=100),
            UpgradeCandidate(name="Second", base_type="Burgonet", item_level=84, total_score=80),
        ]
        result = SlotUpgradeResult(
            slot="Helmet",
            current_item=None,
            candidates=candidates,
        )
        assert result.best_upgrade.name == "Best"

    def test_best_upgrade_none_when_empty(self):
        """Test best_upgrade returns None when no candidates."""
        result = SlotUpgradeResult(
            slot="Helmet",
            current_item=None,
            candidates=[],
        )
        assert result.best_upgrade is None


class TestUpgradeFinderResult:
    """Tests for UpgradeFinderResult dataclass."""

    def test_get_best_upgrades_sorted_by_score(self):
        """Test that get_best_upgrades returns sorted results."""
        result = UpgradeFinderResult(
            profile_name="Test",
            budget_chaos=500,
            slot_results={
                "Helmet": SlotUpgradeResult(
                    slot="Helmet",
                    current_item=None,
                    candidates=[
                        UpgradeCandidate(name="Helm1", base_type="Burgonet", item_level=80, total_score=50),
                    ],
                ),
                "Gloves": SlotUpgradeResult(
                    slot="Gloves",
                    current_item=None,
                    candidates=[
                        UpgradeCandidate(name="Gloves1", base_type="Titan Gauntlets", item_level=82, total_score=100),
                    ],
                ),
            },
        )

        best = result.get_best_upgrades(limit=10)
        assert len(best) == 2
        assert best[0][0] == "Gloves"  # Higher score first
        assert best[0][1].total_score == 100

    def test_get_slot_summary(self):
        """Test slot summary generation."""
        result = UpgradeFinderResult(
            profile_name="Test",
            budget_chaos=500,
            slot_results={
                "Helmet": SlotUpgradeResult(
                    slot="Helmet",
                    current_item=None,
                    error="API error",
                ),
                "Gloves": SlotUpgradeResult(
                    slot="Gloves",
                    current_item=None,
                    candidates=[],
                ),
            },
        )

        summary = result.get_slot_summary()
        assert "Error: API error" in summary["Helmet"]
        assert "No upgrades found" in summary["Gloves"]


class TestUpgradeFinderService:
    """Tests for UpgradeFinderService."""

    def test_init(self, mock_character_manager):
        """Test service initialization."""
        service = UpgradeFinderService(
            character_manager=mock_character_manager,
            league="Standard",
        )
        assert service.league == "Standard"
        assert service.character_manager is mock_character_manager

    def test_find_upgrades_no_profile(self, mock_character_manager):
        """Test find_upgrades when profile not found."""
        mock_character_manager.get_profile.return_value = None

        service = UpgradeFinderService(mock_character_manager)
        result = service.find_upgrades("NonExistent", budget_chaos=500)

        assert result.profile_name == "NonExistent"
        assert result.total_candidates == 0
        assert len(result.slot_results) == 0

    def test_find_upgrades_no_build_stats(self, mock_character_manager):
        """Test find_upgrades when profile has no build stats."""
        profile = CharacterProfile(
            name="Empty",
            build=PoBBuild(),  # No stats
        )
        mock_character_manager.get_profile.return_value = profile

        service = UpgradeFinderService(mock_character_manager)
        result = service.find_upgrades("Empty", budget_chaos=500)

        assert result.total_candidates == 0

    def test_find_upgrades_with_profile(
        self,
        mock_character_manager,
        sample_profile,
    ):
        """Test find_upgrades with a valid profile."""
        mock_character_manager.get_profile.return_value = sample_profile

        # Patch at the import location in upgrade_finder module
        with patch('data_sources.pricing.trade_api.TradeApiSource') as mock_trade_api:
            # Mock trade API to return no results (simpler test)
            mock_source = Mock()
            mock_source._search.return_value = (None, [])
            mock_trade_api.return_value = mock_source

            service = UpgradeFinderService(mock_character_manager)
            result = service.find_upgrades(
                "TestCharacter",
                budget_chaos=500,
                slots=["Helmet"],
            )

            assert result.profile_name == "TestCharacter"
            assert "Helmet" in result.slot_results

    def test_build_upgrade_query_includes_price_filter(
        self,
        mock_character_manager,
        sample_profile,
    ):
        """Test that the query includes price filter."""
        mock_character_manager.get_profile.return_value = sample_profile

        service = UpgradeFinderService(mock_character_manager)

        # Access private method for testing
        from core.bis_calculator import BiSRequirements, StatRequirement
        requirements = BiSRequirements(
            slot="Helmet",
            required_stats=[
                StatRequirement("life", "pseudo.pseudo_total_life", 70, 1, "Life build"),
            ],
        )

        query = service._build_upgrade_query(requirements, budget_chaos=500)

        # Verify price filter structure
        assert "filters" in query["query"]
        assert "trade_filters" in query["query"]["filters"]
        assert "price" in query["query"]["filters"]["trade_filters"]["filters"]
        assert query["query"]["filters"]["trade_filters"]["filters"]["price"]["max"] == 500

    def test_parse_listing(self, mock_character_manager):
        """Test parsing trade API listing."""
        service = UpgradeFinderService(mock_character_manager)

        listing = {
            "id": "abc123",
            "item": {
                "name": "Golem Crown",
                "typeLine": "Royal Burgonet",
                "ilvl": 86,
                "explicitMods": [
                    "+95 to maximum Life",
                    "+42% to Fire Resistance",
                ],
                "implicitMods": [],
            },
            "listing": {
                "price": {
                    "amount": 50,
                    "currency": "chaos",
                },
            },
        }

        candidate = service._parse_listing(listing)

        assert candidate is not None
        assert candidate.name == "Golem Crown Royal Burgonet"
        assert candidate.item_level == 86
        assert candidate.price_chaos == 50
        assert candidate.price_display == "50 chaos"
        assert len(candidate.explicit_mods) == 2

    def test_parse_listing_divine_conversion(self, mock_character_manager):
        """Test that divine prices are converted to chaos."""
        service = UpgradeFinderService(mock_character_manager)

        listing = {
            "id": "abc123",
            "item": {
                "name": "",
                "typeLine": "Royal Burgonet",
                "ilvl": 84,
                "explicitMods": [],
                "implicitMods": [],
            },
            "listing": {
                "price": {
                    "amount": 2,
                    "currency": "divine",
                },
            },
        }

        candidate = service._parse_listing(listing)

        assert candidate.price_display == "2 divine"
        assert candidate.price_chaos == 360  # 2 * 180

    def test_score_candidate(self, mock_character_manager, sample_build_stats):
        """Test candidate scoring."""
        service = UpgradeFinderService(mock_character_manager)

        build_stats = BuildStats.from_pob_stats(sample_build_stats)
        from core.upgrade_calculator import UpgradeCalculator
        upgrade_calc = UpgradeCalculator(build_stats)

        candidate = UpgradeCandidate(
            name="Better Helm",
            base_type="Royal Burgonet",
            item_level=84,
            explicit_mods=[
                "+100 to maximum Life",
                "+45% to Fire Resistance",
                "+35% to Cold Resistance",
            ],
            price_chaos=100,
        )

        current_mods = [
            "+70 to maximum Life",
            "+30% to Fire Resistance",
        ]

        service._score_candidate(
            candidate=candidate,
            current_mods=current_mods,
            upgrade_calculator=upgrade_calc,
            dps_calculator=None,
        )

        # Should have positive upgrade score
        assert candidate.upgrade_score > 0
        assert candidate.total_score > 0
        assert candidate.upgrade_impact is not None


class TestBisToPoBSlotMapping:
    """Tests for slot name mapping."""

    def test_standard_slots_mapped(self):
        """Test that standard slots are correctly mapped."""
        assert BIS_TO_POB_SLOT["Helmet"] == "Helmet"
        assert BIS_TO_POB_SLOT["Body Armour"] == "Body Armour"
        assert BIS_TO_POB_SLOT["Gloves"] == "Gloves"
        assert BIS_TO_POB_SLOT["Boots"] == "Boots"

    def test_ring_defaults_to_ring1(self):
        """Test that Ring maps to Ring 1."""
        assert BIS_TO_POB_SLOT["Ring"] == "Ring 1"

    def test_shield_maps_to_offhand(self):
        """Test that Shield maps to Weapon 2 (offhand)."""
        assert BIS_TO_POB_SLOT["Shield"] == "Weapon 2"
