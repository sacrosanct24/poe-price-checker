# core/app_context.py
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from core.game_version import GameVersion, GameConfig
from data_sources.pricing.poe_ninja import PoeNinjaAPI
from core.price_service import PriceService
from core.price_multi import (
    MultiSourcePriceService,
    ExistingServiceAdapter,
    PriceSource,
)
from data_sources.pricing.trade_api import PoeTradeClient, TradeApiSource

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
    """
    config: Config
    parser: ItemParser
    db: Database
    poe_ninja: PoeNinjaAPI | None  # None when current game is PoE2 (until PoE2 support exists)
    price_service: MultiSourcePriceService


def create_app_context() -> AppContext:
    config = Config()
    parser = ItemParser()
    db = Database()  # Uses default ~/.poe_price_checker/data.db

    game: GameVersion = config.current_game
    game_cfg: GameConfig = config.get_game_config(game)

    poe_ninja: PoeNinjaAPI | None = None
    if game == GameVersion.POE1:
        # Start with whatever league is in the config
        poe_ninja = PoeNinjaAPI(league=game_cfg.league)

        # Optionally auto-detect the active temp league via poe.ninja
        if config.auto_detect_league:
            logger = logging.getLogger(__name__)
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

    # ------------------------------------------------------------------
    # Base single-source price service (existing implementation)
    # ------------------------------------------------------------------
    price_logger = logging.getLogger("poe_price_checker.price_service")
    base_price_service = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        logger=price_logger,
    )

    # ------------------------------------------------------------------
    # Multi-source aggregation layer
    # ------------------------------------------------------------------
    base_source: PriceSource = ExistingServiceAdapter(
        name="poe_ninja",  # appears in the 'source' column in the GUI
        service=base_price_service,
    )

    sources: list[PriceSource] = [base_source]

    # --- (SKELETON) Trade API source wiring ---------------------------
    if game == GameVersion.POE1:
        trade_logger = logging.getLogger("poe_price_checker.trade_api")
        trade_client = PoeTradeClient(logger=trade_logger)

        trade_source = TradeApiSource(
            name="trade_api",
            client=trade_client,
            league=game_cfg.league,
            logger=trade_logger,
        )

        # NOTE: search_and_fetch is a stub for now, so this won't add rows yet.
        # Once implemented, simply leave this append in place.
        sources.append(trade_source)
    # -------------------------------------------------------------------

    multi_price_service = MultiSourcePriceService(sources=sources)

    return AppContext(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        price_service=multi_price_service,
    )
