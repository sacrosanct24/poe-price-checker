# tests/test_app_context_league.py

from dataclasses import dataclass

import core.app_context as appctx
from core.game_version import GameVersion, GameConfig


@dataclass
class DummyConfig:
    """
    Minimal stand-in for core.config.Config used in this test.

    We only need:
      - current_game
      - auto_detect_league
      - get_game_config()
    """
    current_game: GameVersion = GameVersion.POE1
    auto_detect_league: bool = False  # ensure create_app_context doesn't try detection

    def get_game_config(self, game: GameVersion) -> GameConfig:
        # For this test, we only care about PoE1 and the league
        assert game == GameVersion.POE1
        return GameConfig(GameVersion.POE1, league="Keepers")


class DummyDatabase:
    """No-op replacement for Database; avoids touching the filesystem."""
    def __init__(self, *args, **kwargs):
        self.closed = False

    def close(self):
        self.closed = True


class DummyPoeNinja:
    """Capture the league that create_app_context passes in."""
    def __init__(self, league: str = "Standard", *args, **kwargs):
        self.league = league


def test_create_app_context_uses_game_config_league(monkeypatch):
    """
    Ensure that create_app_context wires PoeNinjaAPI with the league
    from GameConfig for the current game (PoE1).
    """

    # Patch Config, Database, and PoeNinjaAPI inside core.app_context
    monkeypatch.setattr(appctx, "Config", DummyConfig)
    monkeypatch.setattr(appctx, "Database", DummyDatabase)
    monkeypatch.setattr(appctx, "PoeNinjaAPI", DummyPoeNinja)

    ctx = appctx.create_app_context()

    # Config should be our DummyConfig
    assert isinstance(ctx.config, DummyConfig)

    # DB should be DummyDatabase
    assert isinstance(ctx.db, DummyDatabase)

    # PoeNinjaAPI should be instantiated with league "Keepers"
    assert isinstance(ctx.poe_ninja, DummyPoeNinja)
    assert ctx.poe_ninja.league == "Keepers"
