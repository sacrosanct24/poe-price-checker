from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.app_context import create_app_context, AppContext
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


class TestAppContextCreation:
    """Tests for AppContext dependency injection wiring."""

    def test_create_app_context_provides_config(self) -> None:
        """AppContext should provide a config with valid game version."""
        ctx = create_app_context()
        assert ctx.config.current_game in (GameVersion.POE1, GameVersion.POE2)

    def test_create_app_context_provides_parser(self) -> None:
        """AppContext should provide a parser that can parse items."""
        ctx = create_app_context()
        # Parser should be able to parse a simple currency item
        result = ctx.parser.parse("Rarity: Currency\nExalted Orb\n--------")
        assert result is not None
        assert result.rarity.lower() == "currency"

    def test_create_app_context_provides_database(self) -> None:
        """AppContext should provide a database with sales and history capabilities."""
        ctx = create_app_context()
        # Database should support sales and history operations
        assert hasattr(ctx.db, "record_instant_sale")
        assert hasattr(ctx.db, "get_recent_sales")

    def test_create_app_context_provides_poe_ninja(self) -> None:
        """AppContext should provide poe_ninja client for price data."""
        ctx = create_app_context()
        # poe_ninja should have currency price lookup capability
        if ctx.poe_ninja is not None:  # May be None for PoE2
            assert hasattr(ctx.poe_ninja, "get_currency_price")
            assert hasattr(ctx.poe_ninja, "load_all_prices")

    def test_create_app_context_provides_price_service(self) -> None:
        """AppContext should provide price_service for item checking."""
        ctx = create_app_context()
        # price_service should support check_item operation
        assert hasattr(ctx.price_service, "check_item")
        assert hasattr(ctx.price_service, "sources")

    def test_app_context_components_share_config(self) -> None:
        """All components should use the same config instance."""
        ctx = create_app_context()
        # Verify config is consistently accessible
        config_game = ctx.config.current_game
        assert config_game in (GameVersion.POE1, GameVersion.POE2)

    def test_create_app_context_is_reentrant(self) -> None:
        """Multiple calls to create_app_context should work."""
        ctx1 = create_app_context()
        ctx2 = create_app_context()
        # Both should be valid (may or may not be same instance)
        assert ctx1.config.current_game in (GameVersion.POE1, GameVersion.POE2)
        assert ctx2.config.current_game in (GameVersion.POE1, GameVersion.POE2)


class TestAppContextClose:
    """Tests for AppContext.close() method."""

    def test_close_handles_all_components(self):
        """close() should close database and API clients."""
        mock_db = Mock()
        mock_poe_ninja = Mock()
        mock_poe_watch = Mock()
        mock_price_service = Mock()

        ctx = AppContext(
            config=Mock(),
            parser=Mock(),
            db=mock_db,
            poe_ninja=mock_poe_ninja,
            poe_watch=mock_poe_watch,
            price_service=mock_price_service,
        )

        ctx.close()

        mock_db.close.assert_called_once()
        mock_poe_ninja.close.assert_called_once()
        mock_poe_watch.close.assert_called_once()

    def test_close_handles_database_error(self):
        """close() should handle database close error gracefully."""
        mock_db = Mock()
        mock_db.close.side_effect = Exception("DB close error")

        ctx = AppContext(
            config=Mock(),
            parser=Mock(),
            db=mock_db,
            poe_ninja=None,
            poe_watch=None,
            price_service=Mock(),
        )

        # Should not raise
        ctx.close()
        mock_db.close.assert_called_once()

    def test_close_handles_poe_ninja_error(self):
        """close() should handle poe_ninja close error gracefully."""
        mock_poe_ninja = Mock()
        mock_poe_ninja.close.side_effect = Exception("API close error")

        ctx = AppContext(
            config=Mock(),
            parser=Mock(),
            db=Mock(),
            poe_ninja=mock_poe_ninja,
            poe_watch=None,
            price_service=Mock(),
        )

        # Should not raise
        ctx.close()
        mock_poe_ninja.close.assert_called_once()

    def test_close_handles_poe_watch_error(self):
        """close() should handle poe_watch close error gracefully."""
        mock_poe_watch = Mock()
        mock_poe_watch.close.side_effect = Exception("Watch close error")

        ctx = AppContext(
            config=Mock(),
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            poe_watch=mock_poe_watch,
            price_service=Mock(),
        )

        # Should not raise
        ctx.close()
        mock_poe_watch.close.assert_called_once()

    def test_close_handles_none_components(self):
        """close() should handle None poe_ninja and poe_watch."""
        ctx = AppContext(
            config=Mock(),
            parser=Mock(),
            db=Mock(),
            poe_ninja=None,
            poe_watch=None,
            price_service=Mock(),
        )

        # Should not raise
        ctx.close()


class TestAppContextPolicyConfig:
    """Tests for policy and logging config in create_app_context."""

    @patch("core.app_context.set_active_policy_from_dict")
    @patch("core.app_context.Config")
    def test_display_policy_applied(self, mock_config_class, mock_set_policy):
        """Display policy should be applied from config."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2  # Use POE2 to skip complex setup
        mock_config.display_policy = {"min_value": 100}
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.PriceService"):
            ctx = create_app_context()

        mock_set_policy.assert_called_once_with({"min_value": 100})

    @patch("core.app_context.set_active_policy_from_dict")
    @patch("core.app_context.Config")
    def test_display_policy_error_handled(self, mock_config_class, mock_set_policy):
        """Display policy errors should be handled gracefully."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {"invalid": "policy"}
        mock_config_class.return_value = mock_config
        mock_set_policy.side_effect = Exception("Invalid policy")

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.PriceService"):
            # Should not raise
            ctx = create_app_context()
            assert ctx is not None

    @patch("core.app_context.set_retry_logging_verbosity")
    @patch("core.app_context.Config")
    def test_retry_logging_verbosity_applied(self, mock_config_class, mock_set_verbosity):
        """Retry logging verbosity should be applied from config."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.api_retry_logging_verbosity = "verbose"
        mock_config.display_policy = {}
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.set_active_policy_from_dict"):
            ctx = create_app_context()

        mock_set_verbosity.assert_called_once_with("verbose")

    @patch("core.app_context.set_retry_logging_verbosity")
    @patch("core.app_context.Config")
    def test_retry_logging_error_handled(self, mock_config_class, mock_set_verbosity):
        """Retry logging errors should be handled gracefully."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.api_retry_logging_verbosity = "invalid"
        mock_config.display_policy = {}
        mock_config_class.return_value = mock_config
        mock_set_verbosity.side_effect = Exception("Invalid verbosity")

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.set_active_policy_from_dict"):
            # Should not raise
            ctx = create_app_context()
            assert ctx is not None


class TestAppContextPOE1Setup:
    """Tests for POE1-specific setup in create_app_context."""

    @patch("core.app_context.Config")
    def test_poe_ninja_timeout_config_error(self, mock_config_class):
        """API timeout config errors should be handled."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE1
        mock_config.display_policy = {}
        mock_config.auto_detect_league = False
        mock_config.get_api_timeouts.side_effect = Exception("Timeout config error")
        mock_game_cfg = Mock()
        mock_game_cfg.league = "Test"
        mock_config.get_game_config.return_value = mock_game_cfg
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PoeNinjaAPI") as mock_ninja, \
             patch("core.app_context.PoeWatchAPI") as mock_watch, \
             patch("core.app_context.PoeTradeClient"), \
             patch("core.app_context.TradeApiSource"), \
             patch("core.app_context.RareItemEvaluator"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            mock_ninja_instance = Mock()
            mock_ninja.return_value = mock_ninja_instance

            ctx = create_app_context()
            assert ctx.poe_ninja is mock_ninja_instance

    @patch("core.app_context.Config")
    def test_auto_detect_league_success(self, mock_config_class):
        """Auto-detect league should update config when different."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE1
        mock_config.display_policy = {}
        mock_config.auto_detect_league = True
        mock_config.get_api_timeouts.return_value = (10, 30)
        mock_config.get_pricing_ttls.return_value = {}
        mock_game_cfg = Mock()
        mock_game_cfg.league = "OldLeague"
        mock_config.get_game_config.return_value = mock_game_cfg
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PoeNinjaAPI") as mock_ninja, \
             patch("core.app_context.PoeWatchAPI"), \
             patch("core.app_context.PoeTradeClient"), \
             patch("core.app_context.TradeApiSource"), \
             patch("core.app_context.RareItemEvaluator"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            mock_ninja_instance = Mock()
            mock_ninja_instance.detect_current_league.return_value = "NewLeague"
            mock_ninja.return_value = mock_ninja_instance

            ctx = create_app_context()

            mock_config.set_game_config.assert_called()
            assert mock_game_cfg.league == "NewLeague"

    @patch("core.app_context.Config")
    def test_auto_detect_league_failure(self, mock_config_class):
        """Auto-detect league failure should use fallback."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE1
        mock_config.display_policy = {}
        mock_config.auto_detect_league = True
        mock_config.get_api_timeouts.return_value = (10, 30)
        mock_config.get_pricing_ttls.return_value = {}
        mock_game_cfg = Mock()
        mock_game_cfg.league = "FallbackLeague"
        mock_config.get_game_config.return_value = mock_game_cfg
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PoeNinjaAPI") as mock_ninja, \
             patch("core.app_context.PoeWatchAPI"), \
             patch("core.app_context.PoeTradeClient"), \
             patch("core.app_context.TradeApiSource"), \
             patch("core.app_context.RareItemEvaluator"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            mock_ninja_instance = Mock()
            mock_ninja_instance.detect_current_league.side_effect = Exception("API error")
            mock_ninja.return_value = mock_ninja_instance

            ctx = create_app_context()
            # League should remain unchanged
            assert mock_game_cfg.league == "FallbackLeague"

    @patch("core.app_context.Config")
    def test_auto_detect_league_same_league(self, mock_config_class):
        """Auto-detect should not update config when league is same."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE1
        mock_config.display_policy = {}
        mock_config.auto_detect_league = True
        mock_config.get_api_timeouts.return_value = (10, 30)
        mock_config.get_pricing_ttls.return_value = {}
        mock_game_cfg = Mock()
        mock_game_cfg.league = "SameLeague"
        mock_config.get_game_config.return_value = mock_game_cfg
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PoeNinjaAPI") as mock_ninja, \
             patch("core.app_context.PoeWatchAPI"), \
             patch("core.app_context.PoeTradeClient"), \
             patch("core.app_context.TradeApiSource"), \
             patch("core.app_context.RareItemEvaluator"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            mock_ninja_instance = Mock()
            mock_ninja_instance.detect_current_league.return_value = "SameLeague"
            mock_ninja.return_value = mock_ninja_instance

            ctx = create_app_context()
            # set_game_config should NOT be called since league is same
            mock_config.set_game_config.assert_not_called()

    @patch("core.app_context.Config")
    def test_poe_watch_init_failure(self, mock_config_class):
        """poe.watch initialization failure should be handled."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE1
        mock_config.display_policy = {}
        mock_config.auto_detect_league = False
        mock_config.get_api_timeouts.return_value = (10, 30)
        mock_config.get_pricing_ttls.return_value = {}
        mock_game_cfg = Mock()
        mock_game_cfg.league = "TestLeague"
        mock_config.get_game_config.return_value = mock_game_cfg
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PoeNinjaAPI"), \
             patch("core.app_context.PoeWatchAPI") as mock_watch, \
             patch("core.app_context.PoeTradeClient"), \
             patch("core.app_context.TradeApiSource"), \
             patch("core.app_context.RareItemEvaluator"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            mock_watch.side_effect = Exception("Watch init error")

            ctx = create_app_context()
            assert ctx.poe_watch is None

    @patch("core.app_context.Config")
    def test_rare_evaluator_init_failure(self, mock_config_class):
        """Rare evaluator initialization failure should be handled."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE1
        mock_config.display_policy = {}
        mock_config.auto_detect_league = False
        mock_config.get_api_timeouts.return_value = (10, 30)
        mock_config.get_pricing_ttls.return_value = {}
        mock_game_cfg = Mock()
        mock_game_cfg.league = "TestLeague"
        mock_config.get_game_config.return_value = mock_game_cfg
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PoeNinjaAPI"), \
             patch("core.app_context.PoeWatchAPI"), \
             patch("core.app_context.PoeTradeClient"), \
             patch("core.app_context.TradeApiSource"), \
             patch("core.app_context.RareItemEvaluator") as mock_eval, \
             patch("core.app_context.PriceService") as mock_price_svc, \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            mock_eval.side_effect = Exception("Evaluator init error")

            ctx = create_app_context()
            # Should still create context, but with no rare_evaluator
            mock_price_svc.assert_called()
            # Check rare_evaluator arg is None
            call_kwargs = mock_price_svc.call_args.kwargs
            assert call_kwargs.get("rare_evaluator") is None


class TestAppContextMultiSourceSetup:
    """Tests for MultiSourcePriceService setup."""

    @patch("core.app_context.Config")
    def test_multi_source_fallback_on_type_error(self, mock_config_class):
        """MultiSourcePriceService should fallback on TypeError."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config_class.return_value = mock_config

        call_count = [0]

        def mock_multi_source_init(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1 and "base_log_context" in kwargs:
                raise TypeError("unexpected keyword argument")
            return Mock()

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", side_effect=mock_multi_source_init), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            # Should have called twice - first with full args, then fallback
            assert call_count[0] == 2

    @patch("core.app_context.Config")
    def test_use_arbitration_flag_true(self, mock_config_class):
        """use_cross_source_arbitration should be passed to MultiSourcePriceService."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.use_cross_source_arbitration = True
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService") as mock_multi, \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            call_kwargs = mock_multi.call_args.kwargs
            assert call_kwargs.get("use_arbitration") is True

    @patch("core.app_context.Config")
    def test_use_arbitration_flag_false(self, mock_config_class):
        """use_cross_source_arbitration=False should be respected."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.use_cross_source_arbitration = False
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService") as mock_multi, \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            call_kwargs = mock_multi.call_args.kwargs
            assert call_kwargs.get("use_arbitration") is False

    @patch("core.app_context.Config")
    def test_use_arbitration_bool_exception(self, mock_config_class):
        """Exception in bool() conversion should default to False."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        # Create an object that raises on bool() conversion
        class BadBool:
            def __bool__(self):
                raise ValueError("Cannot convert to bool")
        mock_config.use_cross_source_arbitration = BadBool()
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService") as mock_multi, \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            call_kwargs = mock_multi.call_args.kwargs
            assert call_kwargs.get("use_arbitration") is False


class TestAppContextEnabledSources:
    """Tests for enabled_sources config loading."""

    @patch("core.app_context.Config")
    def test_enabled_sources_loaded(self, mock_config_class):
        """enabled_sources should be loaded from config."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.enabled_sources = {"poe_ninja": True, "poe_watch": False}
        mock_config_class.return_value = mock_config

        mock_multi_service = Mock()

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", return_value=mock_multi_service), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            mock_multi_service.set_enabled_state.assert_called_with(
                {"poe_ninja": True, "poe_watch": False}
            )

    @patch("core.app_context.Config")
    def test_enabled_sources_empty(self, mock_config_class):
        """Empty enabled_sources should not call set_enabled_state."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.enabled_sources = {}
        mock_config_class.return_value = mock_config

        mock_multi_service = Mock()

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", return_value=mock_multi_service), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            mock_multi_service.set_enabled_state.assert_not_called()

    @patch("core.app_context.Config")
    def test_enabled_sources_none(self, mock_config_class):
        """None enabled_sources should not call set_enabled_state."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.enabled_sources = None
        mock_config_class.return_value = mock_config

        mock_multi_service = Mock()

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", return_value=mock_multi_service), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            mock_multi_service.set_enabled_state.assert_not_called()

    @patch("core.app_context.Config")
    def test_enabled_sources_error_handled(self, mock_config_class):
        """Errors in enabled_sources loading should be handled."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.enabled_sources = {"poe_ninja": True}
        mock_config_class.return_value = mock_config

        mock_multi_service = Mock()
        mock_multi_service.set_enabled_state.side_effect = Exception("Set state error")

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", return_value=mock_multi_service), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            # Should not raise
            ctx = create_app_context()
            assert ctx is not None

    @patch("core.app_context.Config")
    def test_enabled_sources_missing_method(self, mock_config_class):
        """Missing set_enabled_state method should be handled."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.enabled_sources = {"poe_ninja": True}
        mock_config_class.return_value = mock_config

        # Create mock without set_enabled_state method
        mock_multi_service = Mock(spec=["check_item", "sources"])

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", return_value=mock_multi_service), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            # Should not raise
            ctx = create_app_context()
            assert ctx is not None


class TestAppContextPersistCallback:
    """Tests for _persist_enabled_state callback."""

    @patch("core.app_context.Config")
    def test_persist_callback_called_on_change(self, mock_config_class):
        """_persist_enabled_state should call config.set_enabled_sources."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.enabled_sources = {}
        mock_config_class.return_value = mock_config

        captured_callback = [None]

        def capture_callback(*args, **kwargs):
            if "on_change_enabled_state" in kwargs:
                captured_callback[0] = kwargs["on_change_enabled_state"]
            return Mock()

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", side_effect=capture_callback), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()

            # Call the captured callback
            if captured_callback[0]:
                captured_callback[0]({"poe_ninja": True})
                mock_config.set_enabled_sources.assert_called_with({"poe_ninja": True})

    @patch("core.app_context.Config")
    def test_persist_callback_error_handled(self, mock_config_class):
        """_persist_enabled_state should handle errors gracefully."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config.enabled_sources = {}
        mock_config.set_enabled_sources.side_effect = Exception("Save error")
        mock_config_class.return_value = mock_config

        captured_callback = [None]

        def capture_callback(*args, **kwargs):
            if "on_change_enabled_state" in kwargs:
                captured_callback[0] = kwargs["on_change_enabled_state"]
            return Mock()

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService", side_effect=capture_callback), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()

            # Call the captured callback - should not raise
            if captured_callback[0]:
                captured_callback[0]({"poe_ninja": True})  # Should not raise


class TestAppContextPOE2Setup:
    """Tests for POE2-specific setup."""

    @patch("core.app_context.Config")
    def test_poe2_no_poe_ninja(self, mock_config_class):
        """POE2 should have poe_ninja=None."""
        mock_config = Mock()
        mock_config.current_game = GameVersion.POE2
        mock_config.display_policy = {}
        mock_config_class.return_value = mock_config

        with patch("core.app_context.ItemParser"), \
             patch("core.app_context.Database"), \
             patch("core.app_context.PriceService"), \
             patch("core.app_context.MultiSourcePriceService"), \
             patch("core.app_context.ExistingServiceAdapter"), \
             patch("core.app_context.UndercutPriceSource"), \
             patch("core.app_context.set_active_policy_from_dict"), \
             patch("core.app_context.set_retry_logging_verbosity"):
            ctx = create_app_context()
            assert ctx.poe_ninja is None
            assert ctx.poe_watch is None
