# core/app_context.py
from __future__ import annotations

from dataclasses import dataclass

from core.config import Config
from core.item_parser import ItemParser
from core.database import Database
from core.game_version import GameVersion, GameConfig
from data_sources.pricing.poe_ninja import PoeNinjaAPI


@dataclass
class AppContext:
    """
    Aggregates core services used by the GUI and (later) plugins.

    Keeps wiring in one place so the GUI only orchestrates:
    - config: user settings, current game/league
    - parser: item text → ParsedItem
    - db: SQLite persistence (checked items, sales, price history, plugins)
    - poe_ninja: PoE1 pricing API client
    """
    config: Config
    parser: ItemParser
    db: Database
    poe_ninja: PoeNinjaAPI | None  # None when current game is PoE2 (until PoE2 support exists)


def create_app_context() -> AppContext:
    """
    Factory to create the default application context.

    - Loads JSON config
    - Initializes SQLite DB
    - Creates ItemParser
    - Creates PoeNinjaAPI for PoE1 (if current game is PoE1)
    """
    config = Config()
    parser = ItemParser()
    db = Database()  # Uses default ~/.poe_price_checker/data.db

    game: GameVersion = config.current_game
    game_cfg: GameConfig = config.get_game_config(game)

    poe_ninja: PoeNinjaAPI | None = None
    if game == GameVersion.POE1:
        # For now, only PoE1 is wired to poe.ninja
        poe_ninja = PoeNinjaAPI(league=game_cfg.league)

    return AppContext(
        config=config,
        parser=parser,
        db=db,
        poe_ninja=poe_ninja,
    )
