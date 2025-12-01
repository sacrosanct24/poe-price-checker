"""
Tests for Price Integrator Module.

Tests the price integration functionality including:
- PriceResult dataclass
- UpgradeInfo dataclass
- PriceIntegrator class methods
- DummyPriceClient fallback
- Singleton getter functions
"""
import pytest
from unittest.mock import Mock, patch

from core.price_integrator import (
    PriceResult,
    UpgradeInfo,
    PriceIntegrator,
    DummyPriceClient,
    get_price_integrator,
)


class TestUpgradeInfo:
    """Tests for UpgradeInfo dataclass."""

    def test_basic_creation(self):
        """Test creating a basic UpgradeInfo."""
        info = UpgradeInfo(
            is_upgrade=True,
            reasons=["Better life roll", "Higher resistances"],
            compared_slot="Helmet",
        )
        assert info.is_upgrade is True
        assert len(info.reasons) == 2
        assert info.compared_slot == "Helmet"

    def test_not_upgrade(self):
        """Test creating non-upgrade info."""
        info = UpgradeInfo(
            is_upgrade=False,
            reasons=["Lower damage"],
        )
        assert info.is_upgrade is False

    def test_defaults(self):
        """Test default values."""
        info = UpgradeInfo(is_upgrade=False)
        assert info.reasons == []
        assert info.compared_slot is None
        assert info.compared_item_name is None
        assert info.character_name is None

    def test_full_info(self):
        """Test with all fields populated."""
        info = UpgradeInfo(
            is_upgrade=True,
            reasons=["Better stats"],
            compared_slot="Body Armour",
            compared_item_name="Old Chest",
            character_name="MyCharacter",
        )
        assert info.compared_item_name == "Old Chest"
        assert info.character_name == "MyCharacter"


class TestPriceResult:
    """Tests for PriceResult dataclass."""

    def test_basic_creation(self):
        """Test creating a basic PriceResult."""
        result = PriceResult(
            chaos_value=100.0,
            divine_value=0.56,
            confidence="exact",
            source="poe.ninja",
        )
        assert result.chaos_value == 100.0
        assert result.divine_value == 0.56
        assert result.confidence == "exact"
        assert result.source == "poe.ninja"

    def test_display_price_divine(self):
        """Test display price with divine value."""
        result = PriceResult(
            chaos_value=360.0,
            divine_value=2.0,
            confidence="exact",
            source="poe.ninja",
        )
        assert "2.0 divine" in result.display_price

    def test_display_price_chaos(self):
        """Test display price with chaos value."""
        result = PriceResult(
            chaos_value=50.0,
            divine_value=0.28,
            confidence="exact",
            source="poe.ninja",
        )
        assert "50c" in result.display_price

    def test_display_price_less_than_one(self):
        """Test display price with less than 1 chaos."""
        result = PriceResult(
            chaos_value=0.5,
            divine_value=0.0,
            confidence="exact",
            source="static",
        )
        assert result.display_price == "<1c"

    def test_display_range_divine(self):
        """Test display range for divine values."""
        result = PriceResult(
            chaos_value=270.0,
            divine_value=1.5,
            confidence="ml_predicted",
            source="poeprices",
            price_range=(180.0, 360.0),
        )
        result._divine_threshold = 180.0
        range_str = result.display_range
        assert range_str is not None
        assert "divine" in range_str

    def test_display_range_chaos(self):
        """Test display range for chaos values."""
        result = PriceResult(
            chaos_value=50.0,
            divine_value=0.28,
            confidence="ml_predicted",
            source="poeprices",
            price_range=(30.0, 70.0),
        )
        result._divine_threshold = 180.0
        range_str = result.display_range
        assert range_str is not None
        assert "30-70c" in range_str

    def test_display_range_none(self):
        """Test display range when no range available."""
        result = PriceResult(
            chaos_value=50.0,
            divine_value=0.28,
            confidence="exact",
            source="poe.ninja",
        )
        assert result.display_range is None

    def test_notes_default(self):
        """Test notes default to empty list."""
        result = PriceResult(
            chaos_value=10.0,
            divine_value=0.0,
            confidence="unknown",
            source="none",
        )
        assert result.notes == []

    def test_with_ml_confidence(self):
        """Test with ML confidence score."""
        result = PriceResult(
            chaos_value=100.0,
            divine_value=0.56,
            confidence="ml_predicted",
            source="poeprices",
            ml_confidence_score=75.5,
        )
        assert result.ml_confidence_score == 75.5

    def test_with_upgrade_info(self):
        """Test with upgrade info attached."""
        upgrade = UpgradeInfo(is_upgrade=True, reasons=["Better"])
        result = PriceResult(
            chaos_value=100.0,
            divine_value=0.56,
            confidence="exact",
            source="poe.ninja",
            upgrade_info=upgrade,
        )
        assert result.upgrade_info is not None
        assert result.upgrade_info.is_upgrade is True


class TestDummyPriceClient:
    """Tests for DummyPriceClient fallback."""

    def test_get_price_returns_none(self):
        """Test get_price returns None."""
        client = DummyPriceClient()
        assert client.get_price("any_name") is None

    def test_fetch_all_uniques_returns_empty(self):
        """Test fetch_all_uniques returns empty list."""
        client = DummyPriceClient()
        assert client.fetch_all_uniques() == []

    def test_get_meta_uniques_returns_empty(self):
        """Test get_meta_uniques returns empty list."""
        client = DummyPriceClient()
        assert client.get_meta_uniques() == []

    def test_get_high_value_items_returns_empty(self):
        """Test get_high_value_items returns empty list."""
        client = DummyPriceClient()
        assert client.get_high_value_items() == []

    def test_get_divine_value_returns_default(self):
        """Test get_divine_value returns default value."""
        client = DummyPriceClient()
        assert client.get_divine_value() == 180.0


class TestPriceIntegrator:
    """Tests for PriceIntegrator class."""

    def test_initialization_defaults(self):
        """Test default initialization."""
        integrator = PriceIntegrator(league="TestLeague")
        assert integrator.league == "TestLeague"
        assert integrator.use_poeprices is True
        assert integrator.enable_upgrade_check is True
        assert integrator._prices_loaded is False

    def test_initialization_custom(self):
        """Test custom initialization."""
        mock_evaluator = Mock()
        integrator = PriceIntegrator(
            league="Custom",
            evaluator=mock_evaluator,
            use_poeprices=False,
            enable_upgrade_check=False,
        )
        assert integrator.league == "Custom"
        assert integrator.evaluator is mock_evaluator
        assert integrator.use_poeprices is False
        assert integrator.enable_upgrade_check is False

    def test_get_item_class_from_base_exact_match(self):
        """Test exact match base type mapping."""
        integrator = PriceIntegrator()
        assert integrator._get_item_class_from_base("Vaal Regalia") == "Body Armour"
        assert integrator._get_item_class_from_base("Hubris Circlet") == "Helmet"
        assert integrator._get_item_class_from_base("Sorcerer Gloves") == "Gloves"
        assert integrator._get_item_class_from_base("Sorcerer Boots") == "Boots"
        assert integrator._get_item_class_from_base("Stygian Vise") == "Belt"

    def test_get_item_class_from_base_pattern(self):
        """Test pattern-based base type inference."""
        integrator = PriceIntegrator()
        # Pattern matches
        assert integrator._get_item_class_from_base("Some Plate Armor") == "Body Armour"
        assert integrator._get_item_class_from_base("Dragon Helmet") == "Helmet"
        assert integrator._get_item_class_from_base("Iron Gauntlets") == "Gloves"
        assert integrator._get_item_class_from_base("Steel Greaves") == "Boots"
        assert integrator._get_item_class_from_base("Onyx Amulet") == "Amulet"
        assert integrator._get_item_class_from_base("Diamond Ring") == "Ring"

    def test_get_item_class_from_base_empty(self):
        """Test with empty base type."""
        integrator = PriceIntegrator()
        assert integrator._get_item_class_from_base("") == ""
        assert integrator._get_item_class_from_base("unknown thing") == ""

    @patch.object(PriceIntegrator, '_ensure_prices_loaded')
    def test_get_unique_price_not_unique(self, mock_ensure):
        """Test get_unique_price returns None for non-unique items."""
        integrator = PriceIntegrator()
        mock_item = Mock()
        mock_item.rarity = "RARE"

        result = integrator.get_unique_price(mock_item)
        assert result is None

    @patch.object(PriceIntegrator, '_ensure_prices_loaded')
    def test_get_unique_price_found(self, mock_ensure):
        """Test get_unique_price finds item in cache."""
        integrator = PriceIntegrator()
        integrator._unique_prices = {"headhunter": 100000.0}
        integrator._divine_value = 180.0

        mock_item = Mock()
        mock_item.rarity = "UNIQUE"
        mock_item.name = "Headhunter"
        mock_item.base_type = "Leather Belt"
        mock_item.links = 0

        result = integrator.get_unique_price(mock_item)
        assert result is not None
        assert result.chaos_value == 100000.0
        assert result.source == "poe.ninja"

    @patch.object(PriceIntegrator, '_ensure_prices_loaded')
    def test_get_unique_price_not_found(self, mock_ensure):
        """Test get_unique_price when item not in cache."""
        integrator = PriceIntegrator()
        integrator._unique_prices = {}
        integrator._ninja_client = DummyPriceClient()

        mock_item = Mock()
        mock_item.rarity = "UNIQUE"
        mock_item.name = "UnknownUnique"
        mock_item.base_type = "Belt"
        mock_item.links = 0

        result = integrator.get_unique_price(mock_item)
        assert result is None

    def test_get_rare_price_with_evaluator(self):
        """Test get_rare_price using evaluator."""
        mock_evaluator = Mock()
        mock_evaluation = Mock()
        mock_evaluation.tier = "good"
        mock_evaluation.total_score = 65
        mock_evaluation.synergies_found = []
        mock_evaluation.is_fractured = False
        mock_evaluation.fractured_bonus = 0
        mock_evaluation.matched_archetypes = []
        mock_evaluation.matched_affixes = []
        mock_evaluator.evaluate.return_value = mock_evaluation

        integrator = PriceIntegrator(
            league="Test",
            evaluator=mock_evaluator,
            use_poeprices=False,
        )

        mock_item = Mock()
        result = integrator.get_rare_price(mock_item)

        assert result is not None
        assert result.confidence == "estimated"
        assert result.source == "evaluation"

    def test_evaluation_to_chaos_excellent(self):
        """Test evaluation to chaos conversion for excellent tier."""
        mock_evaluator = Mock()
        integrator = PriceIntegrator(evaluator=mock_evaluator)

        mock_eval = Mock()
        mock_eval.tier = "excellent"
        mock_eval.total_score = 95
        mock_eval.synergies_found = []
        mock_eval.is_fractured = False
        mock_eval.fractured_bonus = 0
        mock_eval.matched_archetypes = []
        mock_eval.matched_affixes = []

        chaos, notes = integrator._evaluation_to_chaos(mock_eval)
        # Base 150 * 3.0 (elite score) = 450
        assert chaos >= 400

    def test_evaluation_to_chaos_good(self):
        """Test evaluation to chaos conversion for good tier."""
        mock_evaluator = Mock()
        integrator = PriceIntegrator(evaluator=mock_evaluator)

        mock_eval = Mock()
        mock_eval.tier = "good"
        mock_eval.total_score = 75
        mock_eval.synergies_found = []
        mock_eval.is_fractured = False
        mock_eval.fractured_bonus = 0
        mock_eval.matched_archetypes = []
        mock_eval.matched_affixes = []

        chaos, notes = integrator._evaluation_to_chaos(mock_eval)
        # Base 40 * 1.5 (strong score) = 60
        assert chaos >= 50

    def test_evaluation_to_chaos_with_synergies(self):
        """Test evaluation to chaos with synergy bonus."""
        mock_evaluator = Mock()
        integrator = PriceIntegrator(evaluator=mock_evaluator)

        mock_eval = Mock()
        mock_eval.tier = "good"
        mock_eval.total_score = 60
        mock_eval.synergies_found = ["synergy1", "synergy2"]
        mock_eval.is_fractured = False
        mock_eval.fractured_bonus = 0
        mock_eval.matched_archetypes = []
        mock_eval.matched_affixes = []

        chaos, notes = integrator._evaluation_to_chaos(mock_eval)
        # Base 40 * 1.5 (2 synergies) = 60
        assert chaos >= 50
        assert any("Synergies" in n for n in notes)

    def test_evaluation_to_chaos_fractured(self):
        """Test evaluation to chaos with fractured bonus."""
        mock_evaluator = Mock()
        integrator = PriceIntegrator(evaluator=mock_evaluator)

        mock_eval = Mock()
        mock_eval.tier = "good"
        mock_eval.total_score = 60
        mock_eval.synergies_found = []
        mock_eval.is_fractured = True
        mock_eval.fractured_bonus = 30
        mock_eval.matched_archetypes = []
        mock_eval.matched_affixes = []

        chaos, notes = integrator._evaluation_to_chaos(mock_eval)
        # Base 40 * 1.5 (fractured T1) = 60
        assert chaos >= 50
        assert any("Fractured" in n for n in notes)

    def test_evaluation_to_chaos_vendor(self):
        """Test evaluation to chaos for vendor tier."""
        mock_evaluator = Mock()
        integrator = PriceIntegrator(evaluator=mock_evaluator)

        mock_eval = Mock()
        mock_eval.tier = "vendor"
        mock_eval.total_score = 20
        mock_eval.synergies_found = []
        mock_eval.is_fractured = False
        mock_eval.fractured_bonus = 0
        mock_eval.matched_archetypes = []
        mock_eval.matched_affixes = []

        chaos, notes = integrator._evaluation_to_chaos(mock_eval)
        assert chaos == 1.0

    def test_price_item_unknown_rarity(self):
        """Test pricing item with unknown rarity."""
        integrator = PriceIntegrator(enable_upgrade_check=False)
        mock_item = Mock()
        mock_item.rarity = None

        result = integrator.price_item(mock_item)
        assert result.confidence == "unknown"
        assert result.chaos_value == 0

    @patch.object(PriceIntegrator, 'get_unique_price')
    def test_price_item_unique(self, mock_get_unique):
        """Test pricing unique item."""
        mock_get_unique.return_value = PriceResult(
            chaos_value=1000.0,
            divine_value=5.56,
            confidence="exact",
            source="poe.ninja",
        )

        integrator = PriceIntegrator(enable_upgrade_check=False)
        mock_item = Mock()
        mock_item.rarity = "UNIQUE"

        result = integrator.price_item(mock_item)
        assert result.chaos_value == 1000.0
        assert result.source == "poe.ninja"

    @patch.object(PriceIntegrator, 'get_unique_price')
    def test_price_item_unique_not_found(self, mock_get_unique):
        """Test pricing unique item not in database."""
        mock_get_unique.return_value = None

        integrator = PriceIntegrator(enable_upgrade_check=False)
        mock_item = Mock()
        mock_item.rarity = "UNIQUE"

        result = integrator.price_item(mock_item)
        assert result.confidence == "unknown"
        assert "not found" in result.notes[0]

    @patch.object(PriceIntegrator, 'get_rare_price')
    def test_price_item_rare(self, mock_get_rare):
        """Test pricing rare item."""
        mock_get_rare.return_value = PriceResult(
            chaos_value=50.0,
            divine_value=0.28,
            confidence="estimated",
            source="evaluation",
        )

        integrator = PriceIntegrator(enable_upgrade_check=False)
        mock_item = Mock()
        mock_item.rarity = "RARE"

        result = integrator.price_item(mock_item)
        assert result.chaos_value == 50.0
        assert result.source == "evaluation"

    def test_price_item_normal(self):
        """Test pricing normal item."""
        integrator = PriceIntegrator(enable_upgrade_check=False)
        mock_item = Mock()
        mock_item.rarity = "NORMAL"

        result = integrator.price_item(mock_item)
        assert result.chaos_value == 0
        assert "vendor trash" in result.notes[0]

    def test_get_divine_value(self):
        """Test getting divine value."""
        integrator = PriceIntegrator()
        integrator._divine_value = 200.0
        assert integrator.get_divine_value() == 200.0

    @patch.object(PriceIntegrator, '_ensure_prices_loaded')
    def test_get_high_value_uniques(self, mock_ensure):
        """Test getting high value uniques."""
        integrator = PriceIntegrator()
        integrator._unique_prices = {
            "headhunter": 100000.0,
            "mageblood": 150000.0,
            "tabula rasa": 10.0,
        }
        integrator._divine_value = 180.0

        high_value = integrator.get_high_value_uniques(min_chaos=50)
        assert len(high_value) == 2
        # Should be sorted by value descending
        assert high_value[0]["name"] == "mageblood"
        assert high_value[1]["name"] == "headhunter"

    @patch.object(PriceIntegrator, 'price_item')
    def test_get_price_summary(self, mock_price_item):
        """Test getting formatted price summary."""
        mock_price_item.return_value = PriceResult(
            chaos_value=100.0,
            divine_value=0.56,
            confidence="exact",
            source="poe.ninja",
            notes=["Test note"],
        )

        integrator = PriceIntegrator()
        mock_item = Mock()
        mock_item.get_display_name.return_value = "Test Item"
        mock_item.rarity = "UNIQUE"

        summary = integrator.get_price_summary(mock_item)
        assert "Price Estimate" in summary
        assert "Test Item" in summary
        assert "100c" in summary or "100.0" in summary
        assert "poe.ninja" in summary

    @patch.object(PriceIntegrator, 'price_item')
    def test_get_price_summary_with_upgrade(self, mock_price_item):
        """Test price summary includes upgrade info."""
        mock_price_item.return_value = PriceResult(
            chaos_value=100.0,
            divine_value=0.56,
            confidence="exact",
            source="poe.ninja",
            upgrade_info=UpgradeInfo(
                is_upgrade=True,
                reasons=["Better life"],
                compared_slot="Helmet",
                character_name="TestChar",
            ),
        )

        integrator = PriceIntegrator()
        mock_item = Mock()
        mock_item.get_display_name.return_value = "Test Item"
        mock_item.rarity = "UNIQUE"

        summary = integrator.get_price_summary(mock_item)
        assert "Upgrade Check" in summary
        assert "POTENTIAL UPGRADE" in summary
        assert "TestChar" in summary


class TestPriceIntegratorLazyLoading:
    """Tests for lazy loading properties."""

    def test_ninja_client_lazy_loads(self):
        """Test ninja_client property triggers lazy loading."""
        integrator = PriceIntegrator()
        assert integrator._ninja_client is None

        # Accessing property should attempt to load, might get DummyClient on failure
        # Patch at the import location in the property
        with patch.dict('sys.modules', {'data_sources.pricing.poe_ninja': None}):
            client = integrator.ninja_client
            assert client is not None

    def test_poeprices_client_disabled(self):
        """Test poeprices client is None when disabled."""
        integrator = PriceIntegrator(use_poeprices=False)
        assert integrator.poeprices_client is None

    def test_character_manager_disabled(self):
        """Test character manager is None when upgrade check disabled."""
        integrator = PriceIntegrator(enable_upgrade_check=False)
        assert integrator.character_manager is None


class TestGetPriceIntegrator:
    """Tests for singleton getter function."""

    def test_get_price_integrator_creates_new(self):
        """Test creating new integrator."""
        # Reset global singleton
        import core.price_integrator as module
        module._integrator = None

        integrator = get_price_integrator("TestLeague")
        assert integrator is not None
        assert integrator.league == "TestLeague"

    def test_get_price_integrator_reuses(self):
        """Test reusing existing integrator for same league."""
        import core.price_integrator as module
        module._integrator = None

        integrator1 = get_price_integrator("SameLeague")
        integrator2 = get_price_integrator("SameLeague")
        assert integrator1 is integrator2

    def test_get_price_integrator_creates_new_for_different_league(self):
        """Test creating new integrator for different league."""
        import core.price_integrator as module
        module._integrator = None

        integrator1 = get_price_integrator("League1")
        integrator2 = get_price_integrator("League2")
        # Different leagues should return different instance
        assert integrator1.league != integrator2.league


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
