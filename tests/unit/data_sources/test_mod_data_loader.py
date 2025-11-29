"""Tests for data_sources/mod_data_loader.py - Mod data loader."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from data_sources.mod_data_loader import (
    ModDataLoader,
    ensure_mod_database_updated,
)


class TestModDataLoader:
    """Tests for ModDataLoader class."""

    @pytest.fixture
    def mock_database(self):
        """Create mock database."""
        db = MagicMock()
        db.should_update.return_value = True
        db.get_mod_count.return_value = 0
        db.get_item_count.return_value = 0
        db.get_unique_item_count.return_value = 0
        db.get_last_update_time.return_value = None
        db.get_current_league.return_value = None
        return db

    @pytest.fixture
    def mock_api(self):
        """Create mock API client."""
        api = MagicMock()
        api.get_all_item_mods.return_value = []
        api.get_unique_items.return_value = []
        api.get_all_items.return_value = []
        api.get_divination_cards.return_value = []
        api.get_skill_gems.return_value = []
        api.get_scarabs.return_value = []
        api.get_currency.return_value = []
        return api

    @pytest.fixture
    def loader(self, mock_database, mock_api):
        """Create loader with mocks."""
        return ModDataLoader(database=mock_database, api_client=mock_api)

    def test_init_with_dependencies(self, mock_database, mock_api):
        """Should accept database and API client."""
        loader = ModDataLoader(database=mock_database, api_client=mock_api)

        assert loader.db is mock_database
        assert loader.api is mock_api

    def test_init_creates_defaults(self):
        """Should create default database and API if not provided."""
        with patch('data_sources.mod_data_loader.ModDatabase') as mock_db_class:
            with patch('data_sources.mod_data_loader.CargoAPIClient') as mock_api_class:
                loader = ModDataLoader()

                mock_db_class.assert_called_once()
                mock_api_class.assert_called_once_with(rate_limit=1.0)

    def test_should_update_delegates_to_db(self, loader, mock_database):
        """should_update should delegate to database."""
        mock_database.should_update.return_value = True

        result = loader.should_update("TestLeague")

        mock_database.should_update.assert_called_once_with("TestLeague")
        assert result is True

    def test_load_all_mods_success(self, loader, mock_database, mock_api):
        """Should load mods and update database."""
        mock_api.get_all_item_mods.return_value = [
            {"id": "mod1", "name": "Test Mod 1"},
            {"id": "mod2", "name": "Test Mod 2"},
        ]
        mock_database.insert_mods.return_value = 2

        count = loader.load_all_mods("TestLeague")

        assert count == 2
        mock_api.get_all_item_mods.assert_called_once()
        mock_database.insert_mods.assert_called_once()
        mock_database.set_metadata.assert_any_call('league', 'TestLeague')

    def test_load_all_mods_empty_response(self, loader, mock_database, mock_api):
        """Should return 0 for empty API response."""
        mock_api.get_all_item_mods.return_value = []

        count = loader.load_all_mods("TestLeague")

        assert count == 0
        mock_database.insert_mods.assert_not_called()

    def test_load_all_mods_none_response(self, loader, mock_database, mock_api):
        """Should return 0 for None API response."""
        mock_api.get_all_item_mods.return_value = None

        count = loader.load_all_mods("TestLeague")

        assert count == 0

    def test_load_all_mods_with_params(self, loader, mock_api):
        """Should pass parameters to API."""
        mock_api.get_all_item_mods.return_value = []

        loader.load_all_mods("TestLeague", max_mods=1000, batch_size=100)

        mock_api.get_all_item_mods.assert_called_once_with(
            generation_type=None,
            batch_size=100,
            max_total=1000,
        )

    def test_load_all_mods_updates_metadata(self, loader, mock_database, mock_api):
        """Should update metadata after loading."""
        mock_api.get_all_item_mods.return_value = [{"id": "mod1"}]
        mock_database.insert_mods.return_value = 1

        loader.load_all_mods("Settlers")

        # Verify metadata was set
        calls = mock_database.set_metadata.call_args_list
        keys = [call[0][0] for call in calls]
        assert 'league' in keys
        assert 'last_update' in keys
        assert 'mod_count' in keys

    def test_load_all_mods_raises_on_error(self, loader, mock_api):
        """Should raise exception on API error."""
        mock_api.get_all_item_mods.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            loader.load_all_mods("TestLeague")

    def test_load_specific_affixes(self, loader, mock_database, mock_api):
        """Should load specific affix patterns."""
        mock_api.get_mods_by_stat_text.return_value = [{"id": "mod1"}]
        mock_database.insert_mods.return_value = 1

        count = loader.load_specific_affixes(
            ["%maximum Life%", "%Fire Resistance%"],
            "TestLeague"
        )

        assert count == 4  # 2 patterns x 2 generation types
        assert mock_api.get_mods_by_stat_text.call_count == 4

    def test_load_specific_affixes_handles_errors(self, loader, mock_api):
        """Should continue on pattern errors."""
        mock_api.get_mods_by_stat_text.side_effect = [
            Exception("Error"),
            [],
            [],
            [],
        ]

        count = loader.load_specific_affixes(
            ["%bad pattern%", "%good pattern%"],
            "TestLeague"
        )

        # Should still attempt all patterns
        assert mock_api.get_mods_by_stat_text.call_count >= 2

    def test_load_unique_items(self, loader, mock_database, mock_api):
        """Should load unique items."""
        mock_api.get_unique_items.return_value = [
            {"name": "Headhunter"},
            {"name": "Mageblood"},
        ]
        mock_database.insert_items.return_value = 2

        count = loader.load_unique_items()

        assert count == 2
        mock_database.set_metadata.assert_any_call('unique_item_count', '2')

    def test_load_unique_items_empty(self, loader, mock_api):
        """Should return 0 for empty response."""
        mock_api.get_unique_items.return_value = []

        count = loader.load_unique_items()

        assert count == 0

    def test_load_all_items(self, loader, mock_database, mock_api):
        """Should load all item types."""
        mock_api.get_all_items.return_value = [
            {"name": "Item1"},
            {"name": "Item2"},
            {"name": "Item3"},
        ]
        mock_database.insert_items.return_value = 3

        count = loader.load_all_items()

        assert count == 3

    def test_load_divination_cards(self, loader, mock_database, mock_api):
        """Should load divination cards."""
        mock_api.get_divination_cards.return_value = [{"name": "The Doctor"}]
        mock_database.insert_items.return_value = 1

        count = loader.load_divination_cards()

        assert count == 1

    def test_load_gems(self, loader, mock_database, mock_api):
        """Should load skill gems."""
        mock_api.get_skill_gems.return_value = [{"name": "Spectral Throw"}]
        mock_database.insert_items.return_value = 1

        count = loader.load_gems()

        assert count == 1

    def test_load_scarabs(self, loader, mock_database, mock_api):
        """Should load scarabs."""
        mock_api.get_scarabs.return_value = [{"name": "Gilded Breach Scarab"}]
        mock_database.insert_items.return_value = 1

        count = loader.load_scarabs()

        assert count == 1

    def test_load_currency(self, loader, mock_database, mock_api):
        """Should load currency items."""
        mock_api.get_currency.return_value = [{"name": "Divine Orb"}]
        mock_database.insert_items.return_value = 1

        count = loader.load_currency()

        assert count == 1

    def test_get_stats(self, loader, mock_database):
        """Should return database statistics."""
        mock_database.get_mod_count.return_value = 100
        mock_database.get_item_count.return_value = 50
        mock_database.get_unique_item_count.return_value = 30
        mock_database.get_last_update_time.return_value = datetime(2024, 1, 1)
        mock_database.get_current_league.return_value = "TestLeague"

        stats = loader.get_stats()

        assert stats['mod_count'] == 100
        assert stats['item_count'] == 50
        assert stats['unique_item_count'] == 30
        assert stats['league'] == "TestLeague"


class TestEnsureModDatabaseUpdated:
    """Tests for ensure_mod_database_updated function."""

    def test_updates_when_needed(self):
        """Should update database when needed."""
        with patch('data_sources.mod_data_loader.ModDataLoader') as MockLoader:
            mock_loader = MagicMock()
            mock_loader.should_update.return_value = True
            mock_loader.db = MagicMock()
            MockLoader.return_value = mock_loader

            result = ensure_mod_database_updated("TestLeague")

            mock_loader.load_all_mods.assert_called_once_with("TestLeague")
            mock_loader.load_unique_items.assert_called_once()

    def test_skips_update_when_fresh(self):
        """Should skip update when data is fresh."""
        with patch('data_sources.mod_data_loader.ModDataLoader') as MockLoader:
            mock_loader = MagicMock()
            mock_loader.should_update.return_value = False
            mock_loader.db = MagicMock()
            mock_loader.get_stats.return_value = {
                'mod_count': 100,
                'unique_item_count': 50,
                'league': "TestLeague",
                'last_update': datetime.now(),
            }
            MockLoader.return_value = mock_loader

            result = ensure_mod_database_updated("TestLeague")

            mock_loader.load_all_mods.assert_not_called()

    def test_force_update(self):
        """Should update when force_update=True."""
        with patch('data_sources.mod_data_loader.ModDataLoader') as MockLoader:
            mock_loader = MagicMock()
            mock_loader.should_update.return_value = False
            mock_loader.db = MagicMock()
            MockLoader.return_value = mock_loader

            result = ensure_mod_database_updated("TestLeague", force_update=True)

            mock_loader.load_all_mods.assert_called_once()

    def test_handles_update_error(self):
        """Should continue with existing data on error."""
        with patch('data_sources.mod_data_loader.ModDataLoader') as MockLoader:
            mock_loader = MagicMock()
            mock_loader.should_update.return_value = True
            mock_loader.load_all_mods.side_effect = Exception("API error")
            mock_loader.db = MagicMock()
            MockLoader.return_value = mock_loader

            # Should not raise
            result = ensure_mod_database_updated("TestLeague")

            assert result is mock_loader.db

    def test_loads_items_when_missing(self):
        """Should load items when count is 0."""
        with patch('data_sources.mod_data_loader.ModDataLoader') as MockLoader:
            mock_loader = MagicMock()
            mock_loader.should_update.return_value = False
            mock_loader.db = MagicMock()
            mock_loader.get_stats.return_value = {
                'mod_count': 100,
                'unique_item_count': 0,  # No items loaded
                'league': "TestLeague",
                'last_update': datetime.now(),
            }
            MockLoader.return_value = mock_loader

            result = ensure_mod_database_updated("TestLeague", load_items=True)

            mock_loader.load_unique_items.assert_called_once()

    def test_skips_items_when_disabled(self):
        """Should skip loading items when load_items=False."""
        with patch('data_sources.mod_data_loader.ModDataLoader') as MockLoader:
            mock_loader = MagicMock()
            mock_loader.should_update.return_value = True
            mock_loader.db = MagicMock()
            MockLoader.return_value = mock_loader

            result = ensure_mod_database_updated("TestLeague", load_items=False)

            mock_loader.load_unique_items.assert_not_called()

    def test_returns_database(self):
        """Should return database instance."""
        with patch('data_sources.mod_data_loader.ModDataLoader') as MockLoader:
            mock_loader = MagicMock()
            mock_loader.should_update.return_value = False
            mock_loader.db = MagicMock()
            mock_loader.get_stats.return_value = {
                'mod_count': 100,
                'unique_item_count': 50,
                'league': "TestLeague",
                'last_update': datetime.now(),
            }
            MockLoader.return_value = mock_loader

            result = ensure_mod_database_updated("TestLeague")

            assert result is mock_loader.db
