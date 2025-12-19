"""Tests for core/app_context.py - PoE2 initialization."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.game_version import GameVersion, GameConfig


# ============================================================================
# PoE2 Initialization Tests
# ============================================================================


class TestAppContextPoE2:
    """Tests for PoE2 initialization in create_app_context."""

    @patch('core.app_context.Config')
    @patch('core.app_context.Database')
    @patch('core.app_context.ItemParser')
    @patch('core.app_context.set_active_policy_from_dict')
    @patch('core.app_context.set_retry_logging_verbosity')
    @patch('core.app_context.Poe2NinjaAPI')
    @patch('core.app_context.PoeTradeClient')
    @patch('core.app_context.TradeApiSource')
    @patch('core.app_context.PriceService')
    @patch('core.app_context.MultiSourcePriceService')
    def test_poe2_initializes_poe2_ninja(
        self,
        mock_multi_service,
        mock_price_service,
        mock_trade_source,
        mock_trade_client,
        mock_poe2_ninja,
        mock_retry_verbosity,
        mock_policy,
        mock_parser,
        mock_db,
        mock_config,
    ):
        """Should initialize poe2.ninja when game is PoE2."""
        from core.app_context import create_app_context

        # Setup mock config for PoE2
        config_instance = Mock()
        config_instance.current_game = GameVersion.POE2
        config_instance.get_game_config.return_value = GameConfig(
            game_version=GameVersion.POE2,
            league="Dawn of the Hunt",
        )
        config_instance.display_policy = {}
        config_instance.api_retry_logging_verbosity = "minimal"
        config_instance.get_api_timeouts.return_value = (10, 10)
        config_instance.get_pricing_ttls.return_value = {}
        config_instance.auto_detect_league = False
        config_instance.enabled_sources = {}
        config_instance.use_cross_source_arbitration = False
        mock_config.return_value = config_instance

        # Create context
        create_app_context()

        # Verify poe2.ninja was initialized
        mock_poe2_ninja.assert_called_once_with(league="Dawn of the Hunt")

    @patch('core.app_context.Config')
    @patch('core.app_context.Database')
    @patch('core.app_context.ItemParser')
    @patch('core.app_context.set_active_policy_from_dict')
    @patch('core.app_context.set_retry_logging_verbosity')
    @patch('core.app_context.Poe2NinjaAPI')
    @patch('core.app_context.PoeTradeClient')
    @patch('core.app_context.TradeApiSource')
    @patch('core.app_context.PriceService')
    @patch('core.app_context.MultiSourcePriceService')
    def test_poe2_does_not_initialize_poe_ninja(
        self,
        mock_multi_service,
        mock_price_service,
        mock_trade_source,
        mock_trade_client,
        mock_poe2_ninja,
        mock_retry_verbosity,
        mock_policy,
        mock_parser,
        mock_db,
        mock_config,
    ):
        """Should NOT initialize poe.ninja when game is PoE2."""
        from core.app_context import create_app_context

        # Setup mock config for PoE2
        config_instance = Mock()
        config_instance.current_game = GameVersion.POE2
        config_instance.get_game_config.return_value = GameConfig(
            game_version=GameVersion.POE2,
            league="Standard",
        )
        config_instance.display_policy = {}
        config_instance.api_retry_logging_verbosity = "minimal"
        config_instance.get_api_timeouts.return_value = (10, 10)
        config_instance.get_pricing_ttls.return_value = {}
        config_instance.auto_detect_league = False
        config_instance.enabled_sources = {}
        config_instance.use_cross_source_arbitration = False
        mock_config.return_value = config_instance

        # Create context
        ctx = create_app_context()

        # Verify poe.ninja (PoE1) was NOT initialized - check that poe_ninja is None
        assert ctx.poe_ninja is None

    @patch('core.app_context.Config')
    @patch('core.app_context.Database')
    @patch('core.app_context.ItemParser')
    @patch('core.app_context.set_active_policy_from_dict')
    @patch('core.app_context.set_retry_logging_verbosity')
    @patch('core.app_context.Poe2NinjaAPI')
    @patch('core.app_context.PoeTradeClient')
    @patch('core.app_context.TradeApiSource')
    @patch('core.app_context.PriceService')
    @patch('core.app_context.MultiSourcePriceService')
    def test_poe2_trade_api_uses_poe2_game_version(
        self,
        mock_multi_service,
        mock_price_service,
        mock_trade_source,
        mock_trade_client,
        mock_poe2_ninja,
        mock_retry_verbosity,
        mock_policy,
        mock_parser,
        mock_db,
        mock_config,
    ):
        """Trade API should be initialized with PoE2 game version."""
        from core.app_context import create_app_context

        # Setup mock config for PoE2
        config_instance = Mock()
        config_instance.current_game = GameVersion.POE2
        config_instance.get_game_config.return_value = GameConfig(
            game_version=GameVersion.POE2,
            league="Standard",
        )
        config_instance.display_policy = {}
        config_instance.api_retry_logging_verbosity = "minimal"
        config_instance.get_api_timeouts.return_value = (10, 10)
        config_instance.get_pricing_ttls.return_value = {}
        config_instance.auto_detect_league = False
        config_instance.enabled_sources = {}
        config_instance.use_cross_source_arbitration = False
        mock_config.return_value = config_instance

        # Create context
        create_app_context()

        # Verify PoeTradeClient was called with POE2 game version
        mock_trade_client.assert_called_once()
        call_kwargs = mock_trade_client.call_args[1]
        assert call_kwargs['game_version'] == GameVersion.POE2

    @patch('core.app_context.Config')
    @patch('core.app_context.Database')
    @patch('core.app_context.ItemParser')
    @patch('core.app_context.set_active_policy_from_dict')
    @patch('core.app_context.set_retry_logging_verbosity')
    @patch('core.app_context.Poe2NinjaAPI')
    @patch('core.app_context.PoeTradeClient')
    @patch('core.app_context.TradeApiSource')
    @patch('core.app_context.PriceService')
    @patch('core.app_context.MultiSourcePriceService')
    def test_poe2_price_service_receives_poe2_ninja(
        self,
        mock_multi_service,
        mock_price_service,
        mock_trade_source,
        mock_trade_client,
        mock_poe2_ninja,
        mock_retry_verbosity,
        mock_policy,
        mock_parser,
        mock_db,
        mock_config,
    ):
        """PriceService should receive poe2_ninja and game_version."""
        from core.app_context import create_app_context

        # Setup mock config for PoE2
        config_instance = Mock()
        config_instance.current_game = GameVersion.POE2
        config_instance.get_game_config.return_value = GameConfig(
            game_version=GameVersion.POE2,
            league="Standard",
        )
        config_instance.display_policy = {}
        config_instance.api_retry_logging_verbosity = "minimal"
        config_instance.get_api_timeouts.return_value = (10, 10)
        config_instance.get_pricing_ttls.return_value = {}
        config_instance.auto_detect_league = False
        config_instance.enabled_sources = {}
        config_instance.use_cross_source_arbitration = False
        mock_config.return_value = config_instance

        # Create context
        create_app_context()

        # Verify PriceService was called with poe2_ninja and game_version
        mock_price_service.assert_called_once()
        call_kwargs = mock_price_service.call_args[1]
        assert 'poe2_ninja' in call_kwargs
        assert call_kwargs['game_version'] == GameVersion.POE2


# ============================================================================
# PoE1 Control Tests (ensure PoE1 still works)
# ============================================================================


class TestAppContextPoE1:
    """Control tests to ensure PoE1 initialization still works."""

    @patch('core.app_context.Config')
    @patch('core.app_context.Database')
    @patch('core.app_context.ItemParser')
    @patch('core.app_context.set_active_policy_from_dict')
    @patch('core.app_context.set_retry_logging_verbosity')
    @patch('core.app_context.PoeNinjaAPI')
    @patch('core.app_context.PoeWatchAPI')
    @patch('core.app_context.PoeTradeClient')
    @patch('core.app_context.TradeApiSource')
    @patch('core.app_context.RareItemEvaluator')
    @patch('core.app_context.PriceService')
    @patch('core.app_context.MultiSourcePriceService')
    def test_poe1_initializes_poe_ninja(
        self,
        mock_multi_service,
        mock_price_service,
        mock_rare_eval,
        mock_trade_source,
        mock_trade_client,
        mock_poe_watch,
        mock_poe_ninja,
        mock_retry_verbosity,
        mock_policy,
        mock_parser,
        mock_db,
        mock_config,
    ):
        """Should initialize poe.ninja when game is PoE1."""
        from core.app_context import create_app_context

        # Setup mock config for PoE1
        config_instance = Mock()
        config_instance.current_game = GameVersion.POE1
        config_instance.get_game_config.return_value = GameConfig(
            game_version=GameVersion.POE1,
            league="Standard",
        )
        config_instance.display_policy = {}
        config_instance.api_retry_logging_verbosity = "minimal"
        config_instance.get_api_timeouts.return_value = (10, 10)
        config_instance.get_pricing_ttls.return_value = {}
        config_instance.auto_detect_league = False
        config_instance.enabled_sources = {}
        config_instance.use_cross_source_arbitration = False
        mock_config.return_value = config_instance

        # Create context
        create_app_context()

        # Verify poe.ninja was initialized
        mock_poe_ninja.assert_called_once_with(league="Standard")

    @patch('core.app_context.Config')
    @patch('core.app_context.Database')
    @patch('core.app_context.ItemParser')
    @patch('core.app_context.set_active_policy_from_dict')
    @patch('core.app_context.set_retry_logging_verbosity')
    @patch('core.app_context.PoeNinjaAPI')
    @patch('core.app_context.PoeWatchAPI')
    @patch('core.app_context.PoeTradeClient')
    @patch('core.app_context.TradeApiSource')
    @patch('core.app_context.RareItemEvaluator')
    @patch('core.app_context.PriceService')
    @patch('core.app_context.MultiSourcePriceService')
    def test_poe1_does_not_initialize_poe2_ninja(
        self,
        mock_multi_service,
        mock_price_service,
        mock_rare_eval,
        mock_trade_source,
        mock_trade_client,
        mock_poe_watch,
        mock_poe_ninja,
        mock_retry_verbosity,
        mock_policy,
        mock_parser,
        mock_db,
        mock_config,
    ):
        """Should NOT initialize poe2.ninja when game is PoE1."""
        from core.app_context import create_app_context

        # Setup mock config for PoE1
        config_instance = Mock()
        config_instance.current_game = GameVersion.POE1
        config_instance.get_game_config.return_value = GameConfig(
            game_version=GameVersion.POE1,
            league="Standard",
        )
        config_instance.display_policy = {}
        config_instance.api_retry_logging_verbosity = "minimal"
        config_instance.get_api_timeouts.return_value = (10, 10)
        config_instance.get_pricing_ttls.return_value = {}
        config_instance.auto_detect_league = False
        config_instance.enabled_sources = {}
        config_instance.use_cross_source_arbitration = False
        mock_config.return_value = config_instance

        # Create context
        ctx = create_app_context()

        # Verify poe2_ninja is None
        assert ctx.poe2_ninja is None
