# core/app_context.py
from __future__ import annotations

from dataclasses import dataclass
import logging
from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from core.game_version import GameVersion, GameConfig
from data_sources.pricing.poe_ninja import PoeNinjaAPI
from core.price_service import PriceService


@dataclass
class AppContext:
    """
    Aggregates core services used by the GUI and (later) plugins.

    Keeps wiring in one place so the GUI only orchestrates:
    - config: user settings, current game/league
    - parser: item text → ParsedItem
    - db: SQLite persistence (checked items, sales, price history, plugins)
    - poe_ninja: PoE1 pricing API client
    - price_service: high-level item pricing façade for GUI/CLI
    """
    config: Config
    parser: ItemParser
    db: Database
    poe_ninja: PoeNinjaAPI | None  # None when current game is PoE2 (until PoE2 support exists)
    price_service: PriceService

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

    # Create the high-level price service that the GUI will use
    price_logger = logging.getLogger("poe_price_checker.price_service")
    price_service = PriceService(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        logger=price_logger,
    )

    return AppContext(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
        price_service=price_service,
    )
