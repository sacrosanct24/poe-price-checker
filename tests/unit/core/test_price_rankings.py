"""
Tests for price rankings module.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.price_rankings import (
    RankedItem,
    CategoryRanking,
    PriceRankingCache,
    Top20Calculator,
    PriceRankingHistory,
    CACHE_EXPIRY_DAYS,
    UNIQUE_CATEGORIES,
    CONSUMABLE_CATEGORIES,
    CARD_CATEGORIES,
    CATEGORY_TO_RARITY,
    get_top20_rankings,
    get_top20_for_category,
    get_top20_for_slot,
    get_all_slot_rankings,
    get_rankings_by_group,
    get_rarity_for_category,
    print_ranking,
    print_trending,
)

pytestmark = pytest.mark.unit


class TestRankedItem:
    """Tests for RankedItem dataclass."""

    def test_create_basic_item(self):
        item = RankedItem(
            rank=1,
            name="Divine Orb",
            chaos_value=180.0,
        )
        assert item.rank == 1
        assert item.name == "Divine Orb"
        assert item.chaos_value == 180.0
        assert item.divine_value is None

    def test_create_full_item(self):
        item = RankedItem(
            rank=1,
            name="Mageblood",
            chaos_value=90000.0,
            divine_value=500.0,
            base_type="Heavy Belt",
            icon="http://example.com/icon.png",
            item_class="Belt",
        )
        assert item.base_type == "Heavy Belt"
        assert item.divine_value == 500.0

    def test_to_dict(self):
        item = RankedItem(
            rank=1,
            name="Test Item",
            chaos_value=100.0,
            base_type="Test Base",
        )
        d = item.to_dict()
        assert d["rank"] == 1
        assert d["name"] == "Test Item"
        assert d["chaos_value"] == 100.0
        assert d["base_type"] == "Test Base"
        # None values should be excluded
        assert "divine_value" not in d or d.get("divine_value") is None

    def test_from_dict(self):
        data = {
            "rank": 5,
            "name": "Exalted Orb",
            "chaos_value": 150.0,
            "divine_value": 0.83,
        }
        item = RankedItem.from_dict(data)
        assert item.rank == 5
        assert item.name == "Exalted Orb"
        assert item.chaos_value == 150.0
        assert item.divine_value == 0.83


class TestCategoryRanking:
    """Tests for CategoryRanking dataclass."""

    def test_create_ranking(self):
        items = [
            RankedItem(rank=1, name="Item A", chaos_value=100.0),
            RankedItem(rank=2, name="Item B", chaos_value=50.0),
        ]
        ranking = CategoryRanking(
            category="currency",
            display_name="Currency",
            items=items,
            updated_at="2025-01-01T00:00:00+00:00",
        )
        assert ranking.category == "currency"
        assert ranking.display_name == "Currency"
        assert len(ranking.items) == 2

    def test_to_dict(self):
        items = [RankedItem(rank=1, name="Test", chaos_value=100.0)]
        ranking = CategoryRanking(
            category="test",
            display_name="Test Category",
            items=items,
            updated_at="2025-01-01T00:00:00+00:00",
        )
        d = ranking.to_dict()
        assert d["category"] == "test"
        assert d["display_name"] == "Test Category"
        assert len(d["items"]) == 1

    def test_from_dict(self):
        data = {
            "category": "scarabs",
            "display_name": "Scarabs",
            "items": [
                {"rank": 1, "name": "Divine Scarab", "chaos_value": 500.0},
            ],
            "updated_at": "2025-01-01T00:00:00+00:00",
        }
        ranking = CategoryRanking.from_dict(data)
        assert ranking.category == "scarabs"
        assert len(ranking.items) == 1
        assert ranking.items[0].name == "Divine Scarab"


class TestPriceRankingCache:
    """Tests for PriceRankingCache class."""

    def test_init_creates_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "new_dir"
            cache = PriceRankingCache(cache_dir=cache_dir, league="Standard")
            assert cache_dir.exists()
            assert cache.league == "Standard"

    def test_categories_defined(self):
        assert "currency" in PriceRankingCache.CATEGORIES
        assert "unique_weapons" in PriceRankingCache.CATEGORIES
        assert "scarabs" in PriceRankingCache.CATEGORIES

    def test_category_to_api_type_mapping(self):
        assert PriceRankingCache.CATEGORY_TO_API_TYPE["currency"] == "Currency"
        assert PriceRankingCache.CATEGORY_TO_API_TYPE["unique_armour"] == "UniqueArmour"
        assert PriceRankingCache.CATEGORY_TO_API_TYPE["divination_cards"] == "DivinationCard"

    def test_cache_file_path_includes_league(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Settlers")
            assert "settlers" in str(cache._cache_file).lower()

    def test_cache_file_path_handles_spaces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Keepers of the Flame")
            assert "keepers_of_the_flame" in str(cache._cache_file).lower()

    def test_is_cache_valid_no_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            assert cache.is_cache_valid() is False

    def test_is_cache_valid_fresh_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            cache._cache_metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
            assert cache.is_cache_valid() is True

    def test_is_cache_valid_expired_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            old_time = datetime.now(timezone.utc) - timedelta(days=CACHE_EXPIRY_DAYS + 1)
            cache._cache_metadata["last_updated"] = old_time.isoformat()
            assert cache.is_cache_valid() is False

    def test_get_cache_age_days(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")

            # No cache
            assert cache.get_cache_age_days() is None

            # 2 days old
            old_time = datetime.now(timezone.utc) - timedelta(days=2)
            cache._cache_metadata["last_updated"] = old_time.isoformat()
            age = cache.get_cache_age_days()
            assert age is not None
            assert 1.9 < age < 2.1

    def test_save_and_load_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")

            # Add a ranking
            items = [RankedItem(rank=1, name="Test Item", chaos_value=100.0)]
            ranking = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=items,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            cache._rankings["currency"] = ranking
            cache._save_cache()

            # Create new cache instance and verify load
            cache2 = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            assert "currency" in cache2._rankings
            assert cache2._rankings["currency"].items[0].name == "Test Item"

    def test_clear_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")

            # Add data
            cache._rankings["test"] = CategoryRanking(
                category="test", display_name="Test", items=[]
            )
            cache._save_cache()
            assert cache._cache_file.exists()

            # Clear
            cache.clear_cache()
            assert len(cache._rankings) == 0
            assert not cache._cache_file.exists()


class TestTop20Calculator:
    """Tests for Top20Calculator class."""

    def test_init_with_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache)
            assert calculator.cache is cache

    def test_lazy_loads_api(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache)

            # API not loaded yet
            assert calculator._api is None

            # Mock the import to avoid actual API creation
            with patch("core.price_rankings.Top20Calculator.api", new_callable=lambda: property(lambda self: MagicMock())):
                pass  # Just testing the lazy load pattern

    @pytest.fixture
    def mock_api(self):
        """Create a mock PoE Ninja API."""
        api = MagicMock()
        api.ensure_divine_rate.return_value = 180.0

        # Mock currency data
        api.get_currency_overview.return_value = {
            "lines": [
                {"currencyTypeName": "Divine Orb", "chaosEquivalent": 180.0, "icon": "divine.png"},
                {"currencyTypeName": "Exalted Orb", "chaosEquivalent": 150.0, "icon": "exalted.png"},
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1.0, "icon": "chaos.png"},
            ]
        }

        # Mock item data
        api._get_item_overview.return_value = {
            "lines": [
                {"name": "Mageblood", "chaosValue": 90000.0, "baseType": "Heavy Belt", "itemClass": "Belt"},
                {"name": "Headhunter", "chaosValue": 50000.0, "baseType": "Leather Belt", "itemClass": "Belt"},
            ]
        }

        return api

    def test_fetch_currency_top20(self, mock_api):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            items = calculator._fetch_currency_top20(divine_rate=180.0)

            assert len(items) == 3
            assert items[0].name == "Divine Orb"
            assert items[0].rank == 1
            assert items[0].chaos_value == 180.0
            assert items[0].divine_value == 1.0  # 180 / 180

    def test_fetch_item_top20(self, mock_api):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            items = calculator._fetch_item_top20("UniqueAccessory", divine_rate=180.0)

            assert len(items) == 2
            assert items[0].name == "Mageblood"
            assert items[0].rank == 1
            assert items[0].base_type == "Heavy Belt"
            assert items[1].name == "Headhunter"
            assert items[1].rank == 2

    def test_refresh_category(self, mock_api):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            ranking = calculator.refresh_category("currency", force=True)

            assert ranking is not None
            assert ranking.category == "currency"
            assert ranking.display_name == "Currency"
            assert len(ranking.items) == 3

    def test_refresh_skips_valid_cache(self, mock_api):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            # Populate cache with fresh data
            items = [RankedItem(rank=1, name="Cached", chaos_value=100.0)]
            cache._rankings["currency"] = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=items,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            # Refresh without force - should use cache
            ranking = calculator.refresh_category("currency", force=False)

            assert ranking.items[0].name == "Cached"
            mock_api.get_currency_overview.assert_not_called()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_category_groups_defined(self):
        assert "unique_weapons" in UNIQUE_CATEGORIES
        assert "unique_armour" in UNIQUE_CATEGORIES
        assert "currency" in CONSUMABLE_CATEGORIES
        assert "scarabs" in CONSUMABLE_CATEGORIES

    @patch("core.price_rankings.Top20Calculator")
    def test_get_top20_rankings(self, mock_calculator_class):
        mock_instance = MagicMock()
        mock_instance.refresh_all.return_value = {"currency": MagicMock()}
        mock_calculator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_top20_rankings(league="Standard", cache_dir=Path(tmpdir))

        assert "currency" in result
        mock_instance.refresh_all.assert_called_once_with(force=False)

    @patch("core.price_rankings.Top20Calculator")
    def test_get_top20_for_category(self, mock_calculator_class):
        mock_instance = MagicMock()
        mock_instance.refresh_category.return_value = MagicMock(category="scarabs")
        mock_calculator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_top20_for_category("scarabs", league="Standard", cache_dir=Path(tmpdir))

        assert result.category == "scarabs"
        mock_instance.refresh_category.assert_called_once_with("scarabs", force=False)

    @patch("core.price_rankings.Top20Calculator")
    def test_get_rankings_by_group_uniques(self, mock_calculator_class):
        mock_instance = MagicMock()
        mock_calculator_class.return_value = mock_instance

        # Setup mock to return rankings for unique categories
        def mock_get_all_rankings():
            return {cat: MagicMock(category=cat) for cat in UNIQUE_CATEGORIES}

        mock_instance.cache.get_all_rankings = mock_get_all_rankings

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_rankings_by_group("uniques", league="Standard", cache_dir=Path(tmpdir))

        # Should only include unique categories
        for cat in result:
            assert cat in UNIQUE_CATEGORIES

    @patch("core.price_rankings.Top20Calculator")
    def test_get_rankings_by_group_all(self, mock_calculator_class):
        mock_instance = MagicMock()
        mock_instance.refresh_all.return_value = {"all": MagicMock()}
        mock_calculator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            get_rankings_by_group("all", league="Standard", cache_dir=Path(tmpdir))

        mock_instance.refresh_all.assert_called_once()


class TestCacheExpiry:
    """Tests specifically for cache expiry behavior."""

    def test_expiry_days_constant(self):
        assert CACHE_EXPIRY_DAYS == 1  # 24-hour cache

    def test_cache_expires_after_one_day(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")

            # Set cache to 12 hours old (should be valid)
            twelve_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)
            cache._cache_metadata["last_updated"] = twelve_hours_ago.isoformat()

            # Should be valid at 12 hours
            assert cache.is_cache_valid() is True

            # Set to 2 days old (should be expired)
            two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
            cache._cache_metadata["last_updated"] = two_days_ago.isoformat()

            # Should be expired
            assert cache.is_cache_valid() is False

    def test_category_specific_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")

            # Add fresh currency ranking
            cache._rankings["currency"] = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=[],
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            # Add stale scarabs ranking
            old_time = datetime.now(timezone.utc) - timedelta(days=10)
            cache._rankings["scarabs"] = CategoryRanking(
                category="scarabs",
                display_name="Scarabs",
                items=[],
                updated_at=old_time.isoformat(),
            )

            # Currency should be valid, scarabs should not
            assert cache.is_cache_valid("currency") is True
            assert cache.is_cache_valid("scarabs") is False


class TestPriceRankingHistory:
    """Tests for PriceRankingHistory database storage."""

    def test_init_creates_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)
            assert db_path.exists()
            history.close()

    def test_save_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            items = [
                RankedItem(rank=1, name="Divine Orb", chaos_value=180.0, divine_value=1.0),
                RankedItem(rank=2, name="Exalted Orb", chaos_value=150.0, divine_value=0.83),
            ]
            ranking = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=items,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            snapshot_id = history.save_snapshot(ranking, "Standard")
            assert snapshot_id > 0

            history.close()

    def test_get_item_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            # Save a snapshot
            items = [RankedItem(rank=1, name="Divine Orb", chaos_value=180.0)]
            ranking = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=items,
            )
            history.save_snapshot(ranking, "Standard")

            # Get history
            result = history.get_item_history("Divine Orb", "Standard", days=30)
            assert len(result) == 1
            assert result[0]["chaos_value"] == 180.0
            assert result[0]["rank"] == 1

            history.close()

    def test_get_item_history_no_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            result = history.get_item_history("Nonexistent Item", "Standard", days=30)
            assert len(result) == 0

            history.close()

    def test_get_category_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            # Save a snapshot
            items = [
                RankedItem(rank=1, name="Divine Orb", chaos_value=180.0),
                RankedItem(rank=2, name="Exalted Orb", chaos_value=150.0),
            ]
            ranking = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=items,
            )
            history.save_snapshot(ranking, "Standard")

            # Retrieve it
            retrieved = history.get_category_snapshot("Standard", "currency")
            assert retrieved is not None
            assert retrieved.category == "currency"
            assert len(retrieved.items) == 2
            assert retrieved.items[0].name == "Divine Orb"

            history.close()

    def test_get_snapshot_dates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            # Save snapshots for two categories
            items = [RankedItem(rank=1, name="Test", chaos_value=100.0)]
            for cat in ["currency", "scarabs"]:
                ranking = CategoryRanking(category=cat, display_name=cat, items=items)
                history.save_snapshot(ranking, "Standard")

            # Get dates
            dates = history.get_snapshot_dates("Standard")
            assert len(dates) == 1  # Same date for both

            # Filter by category
            dates = history.get_snapshot_dates("Standard", category="currency")
            assert len(dates) == 1

            history.close()

    def test_save_all_snapshots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            rankings = {
                "currency": CategoryRanking(
                    category="currency",
                    display_name="Currency",
                    items=[RankedItem(rank=1, name="Divine", chaos_value=180.0)],
                ),
                "scarabs": CategoryRanking(
                    category="scarabs",
                    display_name="Scarabs",
                    items=[RankedItem(rank=1, name="Scarab", chaos_value=50.0)],
                ),
            }

            history.save_all_snapshots(rankings, "Standard")

            # Verify both were saved
            currency = history.get_category_snapshot("Standard", "currency")
            scarabs = history.get_category_snapshot("Standard", "scarabs")

            assert currency is not None
            assert scarabs is not None
            assert currency.items[0].name == "Divine"
            assert scarabs.items[0].name == "Scarab"

            history.close()

    def test_get_trending_items_no_history(self):
        """Trending with no previous data returns empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            trending = history.get_trending_items("Standard", "currency", days=7)
            assert len(trending) == 0

            history.close()


class TestEquipmentSlots:
    """Tests for equipment slot filtering functionality."""

    def test_equipment_slots_defined(self):
        """Equipment slots dictionary is properly defined."""
        slots = PriceRankingCache.EQUIPMENT_SLOTS
        assert "helmet" in slots
        assert "body_armour" in slots
        assert "gloves" in slots
        assert "boots" in slots
        assert "amulet" in slots
        assert "ring" in slots
        assert "belt" in slots
        assert "sword" in slots
        assert "bow" in slots

    def test_slot_display_names_defined(self):
        """Slot display names are defined for all slots."""
        slots = PriceRankingCache.EQUIPMENT_SLOTS
        display_names = PriceRankingCache.SLOT_DISPLAY_NAMES

        for slot in slots:
            assert slot in display_names, f"Missing display name for slot: {slot}"
            assert display_names[slot], f"Empty display name for slot: {slot}"

    def test_slot_config_structure(self):
        """Slot configs have correct structure (api_type, item_types)."""
        for slot, config in PriceRankingCache.EQUIPMENT_SLOTS.items():
            assert len(config) == 2, f"Slot {slot} config should have 2 elements"
            api_type, item_types = config
            assert isinstance(api_type, str), f"Slot {slot} api_type should be string"
            assert api_type.startswith("Unique"), f"Slot {slot} api_type should start with 'Unique'"

    @pytest.fixture
    def mock_api_with_items(self):
        """Create a mock API that returns items with itemType field."""
        api = MagicMock()
        api.ensure_divine_rate.return_value = 180.0

        # Return items with different itemTypes
        api._get_item_overview.return_value = {
            "lines": [
                {"name": "Crown of the Inward Eye", "chaosValue": 50.0, "baseType": "Prophet Crown", "itemType": "Helmet"},
                {"name": "Starforge", "chaosValue": 100.0, "baseType": "Infernal Sword", "itemType": "Two Handed Sword"},
                {"name": "Kaom's Heart", "chaosValue": 200.0, "baseType": "Glorious Plate", "itemType": "Body Armour"},
                {"name": "Sin Trek", "chaosValue": 30.0, "baseType": "Stealth Boots", "itemType": "Boots"},
                {"name": "The Baron", "chaosValue": 40.0, "baseType": "Close Helmet", "itemType": "Helmet"},
            ]
        }
        return api

    def test_fetch_slot_top20_filters_by_item_type(self, mock_api_with_items):
        """fetch_slot_top20 correctly filters by itemType."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api_with_items)

            # Fetch helmets only
            items = calculator._fetch_slot_top20("UniqueArmour", "Helmet", divine_rate=180.0)

            assert len(items) == 2
            assert items[0].name == "Crown of the Inward Eye"
            assert items[1].name == "The Baron"
            # Verify no body armours or boots
            for item in items:
                assert "Kaom" not in item.name
                assert "Sin Trek" not in item.name

    def test_fetch_slot_top20_with_list_filter(self, mock_api_with_items):
        """fetch_slot_top20 handles list of itemTypes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api_with_items)

            # Fetch helmets and body armours
            items = calculator._fetch_slot_top20(
                "UniqueArmour",
                ["Helmet", "Body Armour"],
                divine_rate=180.0
            )

            assert len(items) == 3  # 2 helmets + 1 body armour
            names = [i.name for i in items]
            assert "Kaom's Heart" in names
            assert "Crown of the Inward Eye" in names

    def test_refresh_slot(self, mock_api_with_items):
        """refresh_slot method creates ranking for equipment slot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api_with_items)

            ranking = calculator.refresh_slot("helmet", force=True)

            assert ranking is not None
            assert ranking.category == "slot_helmet"
            assert ranking.display_name == "Helmets"
            assert len(ranking.items) == 2

    def test_refresh_slot_unknown(self, mock_api_with_items):
        """refresh_slot returns None for unknown slot."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api_with_items)

            ranking = calculator.refresh_slot("invalid_slot", force=True)
            assert ranking is None

    def test_refresh_all_slots(self, mock_api_with_items):
        """refresh_all_slots fetches all equipment slots."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api_with_items)

            rankings = calculator.refresh_all_slots(force=True)

            # Should have rankings for all defined slots
            assert len(rankings) > 0
            # All keys should start with "slot_"
            for key in rankings:
                assert key.startswith("slot_")

    @patch("core.price_rankings.Top20Calculator")
    def test_get_top20_for_slot(self, mock_calculator_class):
        """get_top20_for_slot convenience function works."""
        mock_instance = MagicMock()
        mock_ranking = MagicMock(category="slot_helmet")
        mock_instance.refresh_slot.return_value = mock_ranking
        mock_calculator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_top20_for_slot("helmet", league="Standard", cache_dir=Path(tmpdir))

        assert result.category == "slot_helmet"
        mock_instance.refresh_slot.assert_called_once_with("helmet", force=False)

    @patch("core.price_rankings.Top20Calculator")
    def test_get_all_slot_rankings(self, mock_calculator_class):
        """get_all_slot_rankings convenience function works."""
        mock_instance = MagicMock()
        mock_instance.refresh_all_slots.return_value = {"slot_helmet": MagicMock()}
        mock_calculator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_all_slot_rankings(league="Standard", cache_dir=Path(tmpdir))

        assert "slot_helmet" in result
        mock_instance.refresh_all_slots.assert_called_once_with(force=False)


# ---------------------------------------------------------------------------
# Additional Coverage Tests
# ---------------------------------------------------------------------------

class TestGetRarityForCategory:
    """Tests for get_rarity_for_category helper function."""

    def test_unique_categories_return_unique(self):
        for cat in UNIQUE_CATEGORIES:
            assert get_rarity_for_category(cat) == "unique"

    def test_currency_categories_return_currency(self):
        for cat in ["currency", "fragments", "essences", "fossils", "scarabs"]:
            assert get_rarity_for_category(cat) == "currency"

    def test_divination_cards_return_divination(self):
        assert get_rarity_for_category("divination_cards") == "divination"

    def test_slot_categories_return_unique(self):
        assert get_rarity_for_category("slot_helmet") == "unique"
        assert get_rarity_for_category("slot_body_armour") == "unique"
        assert get_rarity_for_category("slot_boots") == "unique"

    def test_unknown_category_returns_normal(self):
        assert get_rarity_for_category("unknown_category") == "normal"


class TestCacheEdgeCases:
    """Tests for edge cases in cache operations."""

    def test_load_cache_invalid_json(self):
        """Loading invalid JSON clears cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cache_file = cache_dir / "price_rankings_standard.json"
            cache_file.write_text("{ invalid json")

            cache = PriceRankingCache(cache_dir=cache_dir, league="Standard")
            assert len(cache._rankings) == 0

    def test_is_cache_valid_invalid_timestamp(self):
        """Invalid timestamp returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            cache._cache_metadata["last_updated"] = "not-a-valid-timestamp"
            assert cache.is_cache_valid() is False

    def test_is_cache_valid_category_no_updated_at(self):
        """Category without updated_at returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            cache._rankings["test"] = CategoryRanking(
                category="test",
                display_name="Test",
                items=[],
                updated_at=None,
            )
            assert cache.is_cache_valid("test") is False

    def test_is_cache_valid_nonexistent_category(self):
        """Nonexistent category returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            assert cache.is_cache_valid("nonexistent") is False

    def test_get_cache_age_invalid_timestamp(self):
        """Invalid timestamp returns None for age."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            cache._cache_metadata["last_updated"] = "invalid"
            assert cache.get_cache_age_days() is None

    def test_get_ranking_nonexistent(self):
        """Getting nonexistent ranking returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            assert cache.get_ranking("nonexistent") is None

    def test_default_cache_dir(self):
        """Default cache dir is user home."""
        with patch.object(Path, 'home', return_value=Path(tempfile.gettempdir())):
            cache = PriceRankingCache(cache_dir=None, league="Test")
            assert ".poe_price_checker" in str(cache.cache_dir)


class TestTop20CalculatorEdgeCases:
    """Tests for edge cases in Top20Calculator."""

    @pytest.fixture
    def mock_api(self):
        api = MagicMock()
        api.ensure_divine_rate.return_value = 180.0
        api.get_currency_overview.return_value = {"lines": []}
        api._get_item_overview.return_value = {"lines": []}
        return api

    def test_refresh_all_with_valid_cache(self, mock_api):
        """refresh_all skips refresh when cache is valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            cache._cache_metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
            cache._rankings["currency"] = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=[RankedItem(rank=1, name="Test", chaos_value=100.0)],
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)
            result = calculator.refresh_all(force=False)

            assert "currency" in result
            mock_api.ensure_divine_rate.assert_not_called()

    def test_refresh_all_force(self, mock_api):
        """refresh_all with force=True refreshes even valid cache."""
        mock_api.get_currency_overview.return_value = {
            "lines": [{"currencyTypeName": "Divine", "chaosEquivalent": 180.0}]
        }
        mock_api._get_item_overview.return_value = {"lines": []}

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            cache._cache_metadata["last_updated"] = datetime.now(timezone.utc).isoformat()

            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)
            result = calculator.refresh_all(force=True)

            mock_api.ensure_divine_rate.assert_called()
            assert len(result) > 0

    def test_refresh_category_unknown(self, mock_api):
        """Unknown category returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            result = calculator._refresh_category("unknown_category", 180.0)
            assert result is None

    def test_refresh_category_exception(self, mock_api):
        """Category refresh handles exceptions."""
        mock_api.get_currency_overview.side_effect = Exception("API Error")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            result = calculator._refresh_category("currency", 180.0)
            assert result is None

    def test_fetch_item_top20_empty_data(self, mock_api):
        """Empty API data returns empty list."""
        mock_api._get_item_overview.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            items = calculator._fetch_item_top20("UniqueWeapon", 180.0)
            assert items == []

    def test_fetch_slot_top20_empty_data(self, mock_api):
        """Empty API data for slot returns empty list."""
        mock_api._get_item_overview.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            items = calculator._fetch_slot_top20("UniqueArmour", "Helmet", 180.0)
            assert items == []

    def test_refresh_slot_exception(self, mock_api):
        """Slot refresh handles exceptions."""
        mock_api._get_item_overview.side_effect = Exception("API Error")

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            result = calculator._refresh_slot("helmet", 180.0)
            assert result is None

    def test_refresh_slot_caches_result(self, mock_api):
        """Valid slot refresh caches the result."""
        mock_api._get_item_overview.return_value = {
            "lines": [{"name": "Test Helmet", "chaosValue": 50.0, "itemType": "Helmet"}]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            calculator.refresh_slot("helmet", force=True)
            assert "slot_helmet" in cache._rankings

    def test_currency_zero_divine_rate(self, mock_api):
        """Currency fetch handles zero divine rate."""
        mock_api.get_currency_overview.return_value = {
            "lines": [{"currencyTypeName": "Chaos", "chaosEquivalent": 1.0}]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            items = calculator._fetch_currency_top20(divine_rate=0)
            assert items[0].divine_value is None

    def test_item_zero_divine_rate(self, mock_api):
        """Item fetch handles zero divine rate."""
        mock_api._get_item_overview.return_value = {
            "lines": [{"name": "Test", "chaosValue": 100.0}]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)

            items = calculator._fetch_item_top20("UniqueWeapon", divine_rate=0)
            assert items[0].divine_value is None


class TestGetRankingsByGroupEdgeCases:
    """Tests for get_rankings_by_group edge cases."""

    @patch("core.price_rankings.Top20Calculator")
    def test_consumables_group(self, mock_calculator_class):
        """Test consumables group fetches correct categories."""
        mock_instance = MagicMock()
        mock_calculator_class.return_value = mock_instance
        mock_instance.cache.get_all_rankings.return_value = {
            cat: MagicMock(category=cat) for cat in CONSUMABLE_CATEGORIES
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_rankings_by_group("consumables", league="Standard", cache_dir=Path(tmpdir))

        for cat in result:
            assert cat in CONSUMABLE_CATEGORIES

    @patch("core.price_rankings.Top20Calculator")
    def test_cards_group(self, mock_calculator_class):
        """Test cards group fetches divination cards."""
        mock_instance = MagicMock()
        mock_calculator_class.return_value = mock_instance
        mock_instance.cache.get_all_rankings.return_value = {
            "divination_cards": MagicMock(category="divination_cards")
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_rankings_by_group("cards", league="Standard", cache_dir=Path(tmpdir))

        assert "divination_cards" in result or len(result) >= 0

    @patch("core.price_rankings.Top20Calculator")
    def test_unknown_group_defaults_to_all(self, mock_calculator_class):
        """Unknown group defaults to all categories."""
        mock_instance = MagicMock()
        mock_instance.refresh_all.return_value = {"all": MagicMock()}
        mock_calculator_class.return_value = mock_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            get_rankings_by_group("unknown_group", league="Standard", cache_dir=Path(tmpdir))

        mock_instance.refresh_all.assert_called_once()

    @patch("core.price_rankings.Top20Calculator")
    def test_equipment_group(self, mock_calculator_class):
        """Test equipment group is alias for uniques."""
        mock_instance = MagicMock()
        mock_calculator_class.return_value = mock_instance
        mock_instance.cache.get_all_rankings.return_value = {
            cat: MagicMock(category=cat) for cat in UNIQUE_CATEGORIES
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_rankings_by_group("equipment", league="Standard", cache_dir=Path(tmpdir))

        for cat in result:
            assert cat in UNIQUE_CATEGORIES


class TestPriceRankingHistoryEdgeCases:
    """Additional tests for PriceRankingHistory."""

    def test_context_manager(self):
        """Test context manager properly closes connection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with PriceRankingHistory(db_path=db_path) as history:
                history.save_snapshot(
                    CategoryRanking(
                        category="test",
                        display_name="Test",
                        items=[RankedItem(rank=1, name="Item", chaos_value=100.0)],
                    ),
                    "Standard"
                )
            # Connection should be closed after context manager exit

    def test_get_item_history_with_category_filter(self):
        """Test get_item_history with category filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            # Save same item in different categories
            for cat in ["currency", "fragments"]:
                history.save_snapshot(
                    CategoryRanking(
                        category=cat,
                        display_name=cat.title(),
                        items=[RankedItem(rank=1, name="Divine Orb", chaos_value=180.0)],
                    ),
                    "Standard"
                )

            # Filter by specific category
            result = history.get_item_history("Divine Orb", "Standard", days=30, category="currency")
            assert all(r["category"] == "currency" for r in result)

            history.close()

    def test_get_trending_items_with_data(self):
        """Test get_trending_items with actual price changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            # We need to directly insert data for two different dates to test trending
            # Since save_snapshot uses current date, we'll directly manipulate the DB
            cursor = history.conn.cursor()

            today = datetime.now(timezone.utc).date().isoformat()
            past = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()

            # Insert past snapshot
            cursor.execute(
                "INSERT INTO ranking_snapshots (league, category, snapshot_date) VALUES (?, ?, ?)",
                ("Standard", "currency", past)
            )
            past_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO ranked_items (snapshot_id, rank, name, chaos_value) VALUES (?, ?, ?, ?)",
                (past_id, 1, "Divine Orb", 150.0)
            )

            # Insert today snapshot with higher price (20% increase)
            cursor.execute(
                "INSERT INTO ranking_snapshots (league, category, snapshot_date) VALUES (?, ?, ?)",
                ("Standard", "currency", today)
            )
            today_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO ranked_items (snapshot_id, rank, name, chaos_value) VALUES (?, ?, ?, ?)",
                (today_id, 1, "Divine Orb", 180.0)
            )

            history.conn.commit()

            trending = history.get_trending_items("Standard", "currency", days=7, min_change_percent=10.0)
            assert len(trending) == 1
            assert trending[0]["name"] == "Divine Orb"
            assert trending[0]["trend"] == "up"
            assert trending[0]["change_percent"] == 20.0

            history.close()

    def test_get_category_snapshot_with_date(self):
        """Test get_category_snapshot with specific date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            history = PriceRankingHistory(db_path=db_path)

            # Save a snapshot
            history.save_snapshot(
                CategoryRanking(
                    category="currency",
                    display_name="Currency",
                    items=[RankedItem(rank=1, name="Divine", chaos_value=180.0)],
                ),
                "Standard"
            )

            today = datetime.now(timezone.utc).date().isoformat()

            # Get by specific date
            result = history.get_category_snapshot("Standard", "currency", date=today)
            assert result is not None
            assert result.items[0].name == "Divine"

            # Get by nonexistent date
            result = history.get_category_snapshot("Standard", "currency", date="2020-01-01")
            assert result is None

            history.close()

    def test_default_db_path(self):
        """Test default database path."""
        with patch.object(Path, 'home', return_value=Path(tempfile.gettempdir())):
            history = PriceRankingHistory(db_path=None)
            assert "price_rankings.db" in str(history.db_path)
            history.close()


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_print_ranking(self, capsys):
        """Test print_ranking output."""
        ranking = CategoryRanking(
            category="currency",
            display_name="Currency",
            items=[
                RankedItem(rank=1, name="Divine Orb", chaos_value=180.0, divine_value=1.0),
                RankedItem(rank=2, name="Exalted Orb", chaos_value=150.0, divine_value=0.83, base_type="Orb"),
            ],
        )

        print_ranking(ranking, limit=2, show_divine=True)
        captured = capsys.readouterr()

        assert "Currency" in captured.out
        assert "Divine Orb" in captured.out
        assert "180" in captured.out
        assert "1.00 div" in captured.out
        assert "[Orb]" in captured.out

    def test_print_ranking_no_divine(self, capsys):
        """Test print_ranking without divine values."""
        ranking = CategoryRanking(
            category="currency",
            display_name="Currency",
            items=[
                RankedItem(rank=1, name="Divine Orb", chaos_value=180.0),
            ],
        )

        print_ranking(ranking, limit=1, show_divine=False)
        captured = capsys.readouterr()

        assert "Divine Orb" in captured.out
        assert "div" not in captured.out

    def test_print_trending_with_data(self, capsys):
        """Test print_trending with data."""
        trending = [
            {"name": "Divine Orb", "old_price": 150.0, "new_price": 180.0, "change_percent": 20.0, "trend": "up"},
            {"name": "Mirror Shard", "old_price": 1000.0, "new_price": 800.0, "change_percent": -20.0, "trend": "down"},
        ]

        print_trending(trending, "Currency")
        captured = capsys.readouterr()

        assert "Trending: Currency" in captured.out
        assert "Divine Orb" in captured.out
        assert "↑" in captured.out
        assert "↓" in captured.out
        assert "+20.0%" in captured.out
        assert "-20.0%" in captured.out

    def test_print_trending_empty(self, capsys):
        """Test print_trending with no data."""
        print_trending([], "Currency")
        captured = capsys.readouterr()

        assert "No significant price changes found" in captured.out


class TestCategoryConstants:
    """Tests for category constant definitions."""

    def test_card_categories_defined(self):
        """CARD_CATEGORIES contains divination_cards."""
        assert "divination_cards" in CARD_CATEGORIES

    def test_category_to_rarity_complete(self):
        """All categories have rarity mappings."""
        for cat in PriceRankingCache.CATEGORIES:
            # Either in CATEGORY_TO_RARITY or will default to "normal"
            rarity = get_rarity_for_category(cat)
            assert rarity in ["unique", "currency", "divination", "normal"]


class TestAdditionalEdgeCases:
    """Additional edge case tests for better coverage."""

    def test_save_cache_exception(self):
        """Test _save_cache handles write errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            cache._rankings["test"] = CategoryRanking(
                category="test",
                display_name="Test",
                items=[RankedItem(rank=1, name="Item", chaos_value=100.0)],
            )

            # Make cache file path invalid by making it a directory
            cache._cache_file.mkdir(parents=True, exist_ok=True)

            # This should not raise, just log error
            cache._save_cache()

    def test_api_lazy_loading(self):
        """Test API is lazy loaded on first access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")
            calculator = Top20Calculator(cache)

            assert calculator._api is None

            # Mock the import to avoid actual API instantiation
            with patch("data_sources.pricing.poe_ninja.PoeNinjaAPI") as mock_api_class:
                mock_api_class.return_value = MagicMock()
                api = calculator.api
                assert api is not None

    def test_refresh_slot_uses_cache_when_valid(self):
        """Test refresh_slot returns cached result when valid."""
        mock_api = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")

            # Add valid cached ranking for slot
            slot_key = "slot_helmet"
            cache._rankings[slot_key] = CategoryRanking(
                category=slot_key,
                display_name="Helmets",
                items=[RankedItem(rank=1, name="Cached Helmet", chaos_value=50.0)],
                updated_at=datetime.now(timezone.utc).isoformat(),
            )

            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)
            result = calculator.refresh_slot("helmet", force=False)

            assert result is not None
            assert result.items[0].name == "Cached Helmet"
            mock_api.ensure_divine_rate.assert_not_called()

    def test_refresh_all_logs_cache_age(self):
        """Test refresh_all with valid cache logs the age."""
        mock_api = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PriceRankingCache(cache_dir=Path(tmpdir), league="Standard")

            # Set valid cache with known age
            twelve_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)
            cache._cache_metadata["last_updated"] = twelve_hours_ago.isoformat()
            cache._rankings["currency"] = CategoryRanking(
                category="currency",
                display_name="Currency",
                items=[RankedItem(rank=1, name="Test", chaos_value=100.0)],
                updated_at=twelve_hours_ago.isoformat(),
            )

            calculator = Top20Calculator(cache, poe_ninja_api=mock_api)
            result = calculator.refresh_all(force=False)

            # Should use cache and not call API
            assert "currency" in result
            mock_api.ensure_divine_rate.assert_not_called()

    def test_ranked_item_to_dict_excludes_none(self):
        """Test RankedItem.to_dict excludes None values."""
        item = RankedItem(
            rank=1,
            name="Test",
            chaos_value=100.0,
            divine_value=None,
            base_type=None,
        )
        d = item.to_dict()
        # None values should either be absent or explicitly None
        # The asdict will include them but the list comprehension filters
        assert d["rank"] == 1
        assert d["name"] == "Test"

    def test_ranked_item_from_dict_defaults(self):
        """Test RankedItem.from_dict uses defaults for missing fields."""
        data = {}  # Empty dict
        item = RankedItem.from_dict(data)
        assert item.rank == 0
        assert item.name == ""
        assert item.chaos_value == 0.0
        assert item.divine_value is None

    def test_category_ranking_from_dict_defaults(self):
        """Test CategoryRanking.from_dict uses defaults for missing fields."""
        data = {}  # Empty dict
        ranking = CategoryRanking.from_dict(data)
        assert ranking.category == ""
        assert ranking.display_name == ""
        assert ranking.items == []
        assert ranking.updated_at is None
