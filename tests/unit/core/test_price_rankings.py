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
    get_top20_rankings,
    get_top20_for_category,
    get_top20_for_slot,
    get_all_slot_rankings,
    get_rankings_by_group,
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
