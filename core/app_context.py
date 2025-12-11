# core/app_context.py
from __future__ import annotations

from dataclasses import dataclass
import logging

from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from core.game_version import GameVersion, GameConfig
from core.rare_evaluation import RareItemEvaluator
from data_sources.pricing.poe_ninja import PoeNinjaAPI
from data_sources.pricing.poe_watch import PoeWatchAPI
from core.pricing import PriceService
from core.price_multi import (
    MultiSourcePriceService,
    ExistingServiceAdapter,
    PriceSource,
)
from core.derived_sources import UndercutPriceSource
from data_sources.pricing.trade_api import PoeTradeClient, TradeApiSource
from core.price_estimation import set_active_policy_from_dict
from data_sources.base_api import set_retry_logging_verbosity


@dataclass
class AppContext:
    """
    Aggregates core services used by the GUI and (later) plugins.

    Keeps wiring in one place so the GUI only orchestrates:
    - config: user settings, current game/league
    - parser: item text → ParsedItem
    - db: SQLite persistence (checked items, sales, price history, plugins)
    - poe_ninja: PoE1 pricing API client
    - price_service: high-level *multi-source* item pricing façade for GUI/CLI
      (currently wraps the existing single PriceService, but can host multiple
       PriceSource implementations going forward).

    Call close() when the application exits to release resources.
    """
    config: Config
    parser: ItemParser
    db: Database
    poe_ninja: PoeNinjaAPI | None  # None when current game is PoE2 (until PoE2 support exists)
    poe_watch: PoeWatchAPI | None  # None when disabled or PoE2
    price_service: MultiSourcePriceService

    def close(self) -> None:
        """
        Clean up all resources held by the application context.

        Call this when the application exits to properly close:
        - Database connections
        - HTTP sessions (API clients)
        """
        logger = logging.getLogger(__name__)
        logger.info("Closing AppContext resources...")

        # Close database connection
        if self.db:
            try:
                self.db.close()
                logger.debug("Database closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")

        # Close API client sessions
        if self.poe_ninja:
            try:
                self.poe_ninja.close()
                logger.debug("poe.ninja API closed")
            except Exception as e:
                logger.error(f"Error closing poe.ninja API: {e}")

        if self.poe_watch:
            try:
                self.poe_watch.close()
                logger.debug("poe.watch API closed")
            except Exception as e:
                logger.error(f"Error closing poe.watch API: {e}")

        logger.info("AppContext resources closed")


def create_app_context() -> AppContext:
    config = Config()
    # Apply pricing display policy from config at startup (runtime-tunable)
    try:
        set_active_policy_from_dict(config.display_policy)
    except Exception:
        pass  # Defensive: invalid display_policy config, use defaults
    # Apply API retry logging verbosity
    try:
        set_retry_logging_verbosity(config.api_retry_logging_verbosity)
    except Exception:
        pass  # Defensive: invalid retry logging config, use defaults
    parser = ItemParser()
    db = Database()  # Uses default ~/.poe_price_checker/data.db

    game: GameVersion = config.current_game
    game_cfg: GameConfig = config.get_game_config(game)

    poe_ninja: PoeNinjaAPI | None = None
    poe_watch: PoeWatchAPI | None = None
    logger = logging.getLogger(__name__)

    if game == GameVersion.POE1:
        # Start with whatever league is in the config
        poe_ninja = PoeNinjaAPI(league=game_cfg.league)
        # Apply timeouts and endpoint TTLs from config (non-breaking defaults)
        try:
            connect_to, read_to = config.get_api_timeouts()
            poe_ninja.timeout = (connect_to, read_to)
            poe_ninja.endpoint_ttls = config.get_pricing_ttls()
        except Exception:
            pass  # Defensive: invalid timeout/TTL config, use API defaults

        # Optionally auto-detect the active temp league via poe.ninja
        if config.auto_detect_league:
            try:
                detected = poe_ninja.detect_current_league()
            except Exception as exc:
                logger.warning(
                    "Failed to auto-detect league from poe.ninja; "
                    "using configured league %s. Error: %s",
                    game_cfg.league,
                    exc,
                )
            else:
                if detected and detected != game_cfg.league:
                    logger.info(
                        "Auto-detected current league '%s' (was '%s'); updating config.",
                        detected,
                        game_cfg.league,
                    )
                    # Update the game config + persist
                    game_cfg.league = detected
                    config.set_game_config(game_cfg)

                    # Keep the API client in sync
                    poe_ninja.league = detected

        # Initialize poe.watch as secondary pricing source
        try:
            logger.info("Initializing poe.watch API for league: %s", game_cfg.league)
            poe_watch = PoeWatchAPI(league=game_cfg.league)
            # Apply timeouts and endpoint TTLs from config
            try:
                connect_to, read_to = config.get_api_timeouts()
                poe_watch.timeout = (connect_to, read_to)
                poe_watch.endpoint_ttls = config.get_pricing_ttls()
            except Exception:
                pass  # Defensive: invalid timeout/TTL config, use API defaults
            logger.info("[OK] poe.watch API initialized successfully")
        except Exception as exc:
            logger.warning(
                "Failed to initialize poe.watch API; "
                "continuing with poe.ninja only. Error: %s",
                exc,
            )
            poe_watch = None

    # ------------------------------------------------------------------
    # Trade API source (PoE1 only) – wired into PriceService
    # ------------------------------------------------------------------
    trade_source: TradeApiSource | None = None
    if game == GameVersion.POE1:
        trade_logger = logging.getLogger("poe_price_checker.trade_api")
        trade_client = PoeTradeClient(
            league=game_cfg.league,
            logger=trade_logger,
        )
        trade_source = TradeApiSource(
            name="trade_api",
            client=trade_client,
            league=game_cfg.league,
            logger=trade_logger,
        )

    # ------------------------------------------------------------------
    # Rare item evaluator (PoE1 only)
    # ------------------------------------------------------------------
    rare_evaluator: RareItemEvaluator | None = None
    if game == GameVersion.POE1:
        try:
            logger.info("Initializing rare item evaluator")
            rare_evaluator = RareItemEvaluator()
            logger.info("[OK] Rare item evaluator initialized successfully")
        except Exception as exc:
            logger.warning(
                "Failed to initialize rare item evaluator; "
                "rare pricing will be unavailable. Error: %s",
                exc,
            )
            rare_evaluator = None

    # ------------------------------------------------------------------
    # Base price service with multi-source support
    # Now integrates poe.ninja + poe.watch + trade API + rare evaluator
    # ------------------------------------------------------------------
    price_logger = logging.getLogger("poe_price_checker.price_service")
    base_price_service = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        poe_watch=poe_watch,  # secondary pricing source
        trade_source=trade_source,
        rare_evaluator=rare_evaluator,  # NEW: rare item pricing
        logger=price_logger,
    )

    # ------------------------------------------------------------------
    # Multi-source aggregation layer
    # ------------------------------------------------------------------
    # Wrap the existing PriceService as a PriceSource. This "main" source
    # already uses poe.ninja + trade quotes + DB stats internally.
    base_source: PriceSource = ExistingServiceAdapter(
        name="poe_ninja",  # logical source label for the main row
        service=base_price_service,
    )

    sources: list[PriceSource] = [base_source]

    # Synthetic “derived” source: suggested undercut price based on the
    # main price service output.
    undercut_source: PriceSource = UndercutPriceSource(
        name="suggested_undercut",
        base_service=base_price_service,
        undercut_factor=0.9,  # 10% under poe_ninja by default
    )
    sources.append(undercut_source)

    # NOTE: We do *not* add TradeApiSource directly as a separate PriceSource
    # here. Instead, PriceService uses it internally to enrich poe.ninja
    # stats and DB history. Later, if we want a "raw trade listings" source,
    # we can wrap TradeApiSource in its own PriceSource adapter.

    # Persistence callback for enabled source state
    def _persist_enabled_state(state: dict[str, bool]) -> None:
        try:
            config.set_enabled_sources(state)
        except Exception:
            logging.getLogger(__name__).exception("Failed to persist enabled source state")

    use_arbitration_flag = False
    try:
        use_arbitration_flag = bool(getattr(config, "use_cross_source_arbitration", False))
    except Exception:
        use_arbitration_flag = False

    # Construct multi-source service with backward-compatible fallback for
    # older test doubles that don't accept new keyword arguments.
    try:
        multi_price_service = MultiSourcePriceService(
            sources=sources,
            on_change_enabled_state=_persist_enabled_state,
            base_log_context={
                "game": game.value,
                "league": game_cfg.league,
            },
            use_arbitration=use_arbitration_flag,
        )
    except TypeError:
        # Fallback to minimal constructor signature
        multi_price_service = MultiSourcePriceService(sources=sources)

    # Load enabled sources from config (if any), defaulting to all enabled
    try:
        enabled_map = getattr(config, "enabled_sources", {}) or {}
        if isinstance(enabled_map, dict) and enabled_map:
            # Some older test doubles may not implement set_enabled_state
            if hasattr(multi_price_service, "set_enabled_state"):
                multi_price_service.set_enabled_state(enabled_map)
    except Exception:
        pass  # Defensive: ignore invalid enabled_sources config

    return AppContext(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        poe_watch=poe_watch,
        price_service=multi_price_service,
    )
