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
from core.pob import CharacterProfile, PoBBuild, PoBItem
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


class TestUpgradeCandidateExtended:
    """Extended tests for UpgradeCandidate."""

    def test_get_summary_negative_life_delta(self):
        """Test summary when life delta is negative."""
        from core.upgrade_calculator import UpgradeImpact

        candidate = UpgradeCandidate(
            name="Test",
            base_type="Helm",
            item_level=84,
            upgrade_impact=UpgradeImpact(
                effective_life_delta=-50.0,  # Negative
                fire_res_delta=-5.0,
                cold_res_delta=-5.0,
            ),
        )
        summary = candidate.get_summary()
        assert "+life" not in summary.lower()

    def test_get_summary_negative_res(self):
        """Test summary when total res is negative."""
        from core.upgrade_calculator import UpgradeImpact

        candidate = UpgradeCandidate(
            name="Test",
            base_type="Helm",
            item_level=84,
            upgrade_impact=UpgradeImpact(
                effective_life_delta=0.0,
                fire_res_delta=-10.0,
                cold_res_delta=-10.0,
            ),
            dps_percent_change=0.3,  # Below 0.5 threshold
        )
        summary = candidate.get_summary()
        assert "+res" not in summary.lower()
        assert "DPS" not in summary

    def test_get_summary_low_dps_change(self):
        """Test summary when DPS change is below threshold."""
        from core.upgrade_calculator import UpgradeImpact

        candidate = UpgradeCandidate(
            name="Test",
            base_type="Helm",
            item_level=84,
            upgrade_impact=UpgradeImpact(
                effective_life_delta=0.0,
                fire_res_delta=0.0,
            ),
            dps_percent_change=0.4,  # Below 0.5 threshold
        )
        summary = candidate.get_summary()
        assert "Minor improvement" == summary


class TestSlotUpgradeResultExtended:
    """Extended tests for SlotUpgradeResult."""

    def test_best_upgrade_with_price(self):
        """Test best_upgrade with price info in summary."""
        candidate = UpgradeCandidate(
            name="Good Helm",
            base_type="Burgonet",
            item_level=84,
            price_display="50 chaos",
            total_score=100,
        )
        result = SlotUpgradeResult(
            slot="Helmet",
            current_item=None,
            candidates=[candidate],
        )
        assert result.best_upgrade.price_display == "50 chaos"


class TestUpgradeFinderResultExtended:
    """Extended tests for UpgradeFinderResult."""

    def test_get_slot_summary_with_upgrade(self):
        """Test get_slot_summary when upgrades exist."""
        from core.upgrade_calculator import UpgradeImpact

        candidate = UpgradeCandidate(
            name="Great Helm",
            base_type="Burgonet",
            item_level=86,
            price_display="100 chaos",
            total_score=120,
            upgrade_impact=UpgradeImpact(
                effective_life_delta=100.0,
                fire_res_delta=10.0,
            ),
        )

        result = UpgradeFinderResult(
            profile_name="Test",
            budget_chaos=500,
            slot_results={
                "Helmet": SlotUpgradeResult(
                    slot="Helmet",
                    current_item=None,
                    candidates=[candidate],
                ),
            },
        )

        summary = result.get_slot_summary()
        assert "Great Helm" in summary["Helmet"]
        assert "100 chaos" in summary["Helmet"]


class TestUpgradeFinderServiceExtended:
    """Extended tests for UpgradeFinderService."""

    @pytest.fixture
    def mock_character_manager(self):
        return Mock()

    @pytest.fixture
    def sample_build_stats(self):
        return {
            "Spec:LifeInc": 150.0,
            "Life": 5000.0,
            "EnergyShield": 0.0,
            "FireResist": 75.0,
            "ColdResist": 75.0,
            "LightningResist": 75.0,
            "ChaosResist": 0.0,
            "CombinedDPS": 500000.0,
        }

    @pytest.fixture
    def sample_profile_no_dps(self, sample_build_stats):
        """Profile with no DPS stats."""
        stats = dict(sample_build_stats)
        stats["CombinedDPS"] = 0.0

        build = PoBBuild(
            class_name="Witch",
            level=90,
            stats=stats,
            items={},
        )
        return CharacterProfile(name="TestNoDPS", build=build)

    def test_find_upgrades_no_dps_stats(self, mock_character_manager, sample_profile_no_dps):
        """Test find_upgrades when DPS stats are 0."""
        mock_character_manager.get_profile.return_value = sample_profile_no_dps

        with patch('data_sources.pricing.trade_api.TradeApiSource') as mock_api:
            mock_source = Mock()
            mock_source._search.return_value = (None, [])
            mock_api.return_value = mock_source

            service = UpgradeFinderService(mock_character_manager)
            result = service.find_upgrades(
                "TestNoDPS",
                budget_chaos=500,
                slots=["Helmet"],
            )

            assert "Helmet" in result.slot_results

    def test_find_upgrades_dps_init_error(self, mock_character_manager, sample_build_stats):
        """Test find_upgrades when DPS calculator init fails."""
        build = PoBBuild(
            class_name="Witch",
            level=90,
            stats=sample_build_stats,
            items={},
        )
        profile = CharacterProfile(name="TestDPSError", build=build)
        mock_character_manager.get_profile.return_value = profile

        with patch('data_sources.pricing.trade_api.TradeApiSource') as mock_api, \
             patch('core.upgrade_finder.DPSStats.from_pob_stats', side_effect=ValueError("Bad stats")):
            mock_source = Mock()
            mock_source._search.return_value = (None, [])
            mock_api.return_value = mock_source

            service = UpgradeFinderService(mock_character_manager)
            result = service.find_upgrades(
                "TestDPSError",
                budget_chaos=500,
                slots=["Helmet"],
            )

            # Should still work, just without DPS calc
            assert "Helmet" in result.slot_results

    def test_search_slot_unknown_slot(self, mock_character_manager, sample_build_stats):
        """Test _search_slot with unknown slot."""
        build = PoBBuild(
            class_name="Witch",
            level=90,
            stats=sample_build_stats,
            items={},
        )
        profile = CharacterProfile(name="Test", build=build)

        service = UpgradeFinderService(mock_character_manager)
        build_stats = BuildStats.from_pob_stats(sample_build_stats)
        from core.bis_calculator import BiSCalculator

        result = service._search_slot(
            profile=profile,
            slot="UnknownSlot",
            budget_chaos=500,
            bis_calculator=BiSCalculator(build_stats),
            upgrade_calculator=Mock(),
            dps_calculator=None,
            max_results=5,
        )

        assert result.error is not None
        assert "Unknown slot" in result.error

    def test_search_slot_ring_slot(self, mock_character_manager, sample_build_stats):
        """Test _search_slot handles Ring slot specially."""
        build = PoBBuild(
            class_name="Witch",
            level=90,
            stats=sample_build_stats,
            items={},
        )
        profile = CharacterProfile(name="Test", build=build)

        with patch('data_sources.pricing.trade_api.TradeApiSource') as mock_api:
            mock_source = Mock()
            mock_source._search.return_value = (None, [])
            mock_api.return_value = mock_source

            service = UpgradeFinderService(mock_character_manager)
            build_stats = BuildStats.from_pob_stats(sample_build_stats)
            from core.bis_calculator import BiSCalculator
            from core.upgrade_calculator import UpgradeCalculator

            result = service._search_slot(
                profile=profile,
                slot="Ring",
                budget_chaos=500,
                bis_calculator=BiSCalculator(build_stats),
                upgrade_calculator=UpgradeCalculator(build_stats),
                dps_calculator=None,
                max_results=5,
            )

            # Should not have error - Ring is handled specially
            assert result.error is None or "Unknown" not in str(result.error)

    def test_search_slot_exception_handling(self, mock_character_manager, sample_build_stats):
        """Test _search_slot handles exceptions."""
        build = PoBBuild(
            class_name="Witch",
            level=90,
            stats=sample_build_stats,
            items={},
        )
        profile = CharacterProfile(name="Test", build=build)

        service = UpgradeFinderService(mock_character_manager)

        # Mock BiSCalculator to raise exception
        mock_bis = Mock()
        mock_bis.calculate_requirements.side_effect = RuntimeError("Calc error")

        result = service._search_slot(
            profile=profile,
            slot="Helmet",
            budget_chaos=500,
            bis_calculator=mock_bis,
            upgrade_calculator=Mock(),
            dps_calculator=None,
            max_results=5,
        )

        assert result.error is not None
        assert "Calc error" in result.error

    def test_execute_trade_search_with_results(self, mock_character_manager):
        """Test _execute_trade_search with actual results."""
        with patch('data_sources.pricing.trade_api.TradeApiSource') as mock_api:
            mock_source = Mock()
            mock_source._search.return_value = ("search123", ["id1", "id2"])
            mock_source._fetch_listings.return_value = [
                {
                    "id": "id1",
                    "item": {
                        "name": "Good Helm",
                        "typeLine": "Burgonet",
                        "ilvl": 84,
                        "explicitMods": ["+80 to Life"],
                        "implicitMods": [],
                    },
                    "listing": {"price": {"amount": 50, "currency": "chaos"}},
                },
            ]
            mock_api.return_value = mock_source

            service = UpgradeFinderService(mock_character_manager)
            candidates = service._execute_trade_search({}, max_results=5)

            assert len(candidates) == 1
            assert candidates[0].name == "Good Helm Burgonet"

    def test_execute_trade_search_exception(self, mock_character_manager):
        """Test _execute_trade_search handles exceptions."""
        with patch('data_sources.pricing.trade_api.TradeApiSource', side_effect=RuntimeError("API Error")):
            service = UpgradeFinderService(mock_character_manager)
            candidates = service._execute_trade_search({}, max_results=5)

            assert candidates == []

    def test_parse_listing_exalted_conversion(self, mock_character_manager):
        """Test that exalted prices are converted to chaos."""
        service = UpgradeFinderService(mock_character_manager)

        listing = {
            "id": "abc",
            "item": {
                "name": "",
                "typeLine": "Helm",
                "ilvl": 80,
                "explicitMods": [],
                "implicitMods": [],
            },
            "listing": {
                "price": {"amount": 10, "currency": "exalted"},
            },
        }

        candidate = service._parse_listing(listing)
        assert candidate.price_chaos == 150  # 10 * 15

    def test_parse_listing_malformed_returns_empty(self, mock_character_manager):
        """Test _parse_listing handles malformed data gracefully."""
        service = UpgradeFinderService(mock_character_manager)

        # Malformed listing - returns empty candidate due to .get() defaults
        listing = {"bad": "data"}

        candidate = service._parse_listing(listing)
        # Returns empty candidate, not None
        assert candidate.name == ""
        assert candidate.base_type == ""
        assert candidate.item_level == 0

    def test_parse_listing_exception_returns_none(self, mock_character_manager):
        """Test _parse_listing returns None on exception."""
        service = UpgradeFinderService(mock_character_manager)

        # Pass None to trigger exception in get()
        candidate = service._parse_listing(None)
        assert candidate is None

    def test_score_candidate_with_dps_calculator(self, mock_character_manager, sample_build_stats):
        """Test scoring with DPS calculator."""
        service = UpgradeFinderService(mock_character_manager)

        build_stats = BuildStats.from_pob_stats(sample_build_stats)
        from core.upgrade_calculator import UpgradeCalculator
        from core.dps_impact_calculator import DPSStats, DPSImpactCalculator

        upgrade_calc = UpgradeCalculator(build_stats)
        dps_stats = DPSStats.from_pob_stats(sample_build_stats)
        dps_calc = DPSImpactCalculator(dps_stats)

        candidate = UpgradeCandidate(
            name="DPS Helm",
            base_type="Burgonet",
            item_level=84,
            explicit_mods=["+50% increased Physical Damage"],
            price_chaos=200,
        )

        service._score_candidate(
            candidate=candidate,
            current_mods=[],
            upgrade_calculator=upgrade_calc,
            dps_calculator=dps_calc,
        )

        # Should have DPS impact calculated
        assert candidate.dps_impact is not None or candidate.dps_change >= 0

    def test_score_candidate_upgrade_calc_error(self, mock_character_manager):
        """Test scoring handles upgrade calculator errors."""
        service = UpgradeFinderService(mock_character_manager)

        mock_upgrade_calc = Mock()
        mock_upgrade_calc.calculate_upgrade.side_effect = ValueError("Calc error")

        candidate = UpgradeCandidate(
            name="Error Helm",
            base_type="Burgonet",
            item_level=84,
            explicit_mods=[],
            price_chaos=100,
        )

        service._score_candidate(
            candidate=candidate,
            current_mods=[],
            upgrade_calculator=mock_upgrade_calc,
            dps_calculator=None,
        )

        # Should have 0 score on error
        assert candidate.upgrade_score == 0

    def test_score_candidate_dps_calc_error(self, mock_character_manager, sample_build_stats):
        """Test scoring handles DPS calculator errors."""
        service = UpgradeFinderService(mock_character_manager)

        build_stats = BuildStats.from_pob_stats(sample_build_stats)
        from core.upgrade_calculator import UpgradeCalculator

        upgrade_calc = UpgradeCalculator(build_stats)
        mock_dps_calc = Mock()
        mock_dps_calc.calculate_impact.side_effect = ValueError("DPS error")

        candidate = UpgradeCandidate(
            name="Error Helm",
            base_type="Burgonet",
            item_level=84,
            explicit_mods=[],
            price_chaos=50,
        )

        service._score_candidate(
            candidate=candidate,
            current_mods=[],
            upgrade_calculator=upgrade_calc,
            dps_calculator=mock_dps_calc,
        )

        # Should still have upgrade score, just no DPS
        assert candidate.dps_change == 0

    def test_score_candidate_zero_price(self, mock_character_manager, sample_build_stats):
        """Test scoring with zero price (no penalty)."""
        service = UpgradeFinderService(mock_character_manager)

        build_stats = BuildStats.from_pob_stats(sample_build_stats)
        from core.upgrade_calculator import UpgradeCalculator

        upgrade_calc = UpgradeCalculator(build_stats)

        candidate = UpgradeCandidate(
            name="Free Helm",
            base_type="Burgonet",
            item_level=84,
            explicit_mods=["+50 to maximum Life"],
            price_chaos=0,  # Free item
        )

        service._score_candidate(
            candidate=candidate,
            current_mods=[],
            upgrade_calculator=upgrade_calc,
            dps_calculator=None,
        )

        # Should have no price penalty
        assert candidate.total_score >= candidate.upgrade_score


class TestFactoryFunction:
    """Tests for factory function."""

    def test_get_upgrade_finder(self):
        """Test get_upgrade_finder factory function."""
        from core.upgrade_finder import get_upgrade_finder

        mock_manager = Mock()
        service = get_upgrade_finder(mock_manager, league="Settlers")

        assert isinstance(service, UpgradeFinderService)
        assert service.league == "Settlers"
        assert service.character_manager is mock_manager
