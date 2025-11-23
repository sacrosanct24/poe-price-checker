from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import pytest

import core.app_context as appctx
from core.game_version import GameVersion, GameConfig

pytestmark = pytest.mark.integration


# -------------------------------------------------------------------
# Dummy implementations to intercept create_app_context wiring
# -------------------------------------------------------------------

@dataclass
class DummyConfig:
    """
    Minimal stand-in for core.config.Config used in this test.
    """
    current_game: GameVersion = GameVersion.POE1
    auto_detect_league: bool = False

    def __post_init__(self) -> None:
        self._poe1_cfg = GameConfig(
            game_version=GameVersion.POE1,
            league="Keepers",
            divine_chaos_rate=None,
        )
        self._poe2_cfg = GameConfig(
            game_version=GameVersion.POE2,
            league="Standard",
            divine_chaos_rate=None,
        )
        self.set_game_config_calls: list[GameConfig] = []

    @property
    def league(self) -> str:
        if self.current_game == GameVersion.POE1:
            return self._poe1_cfg.league
        return self._poe2_cfg.league

    def get_game_config(self, game: GameVersion) -> GameConfig:
        if game == GameVersion.POE1:
            return self._poe1_cfg
        return self._poe2_cfg

    def set_game_config(self, cfg: GameConfig) -> None:
        if cfg.game_version == GameVersion.POE1:
            self._poe1_cfg = cfg
        else:
            self._poe2_cfg = cfg
        self.set_game_config_calls.append(cfg)


class DummyDatabase:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class DummyPoeNinja:
    instances: List["DummyPoeNinja"] = []

    def __init__(self, league: str) -> None:
        self.league = league
        self.detect_calls: int = 0
        self.detect_result: str | None = None
        DummyPoeNinja.instances.append(self)

    def detect_current_league(self) -> str | None:
        self.detect_calls += 1
        return self.detect_result


class DummyTradeClient:
    instances: List["DummyTradeClient"] = []

    def __init__(self, league: str, logger=None) -> None:
        self.league = league
        self.logger = logger
        DummyTradeClient.instances.append(self)


class DummyTradeSource:
    instances: List["DummyTradeSource"] = []

    def __init__(self, name: str, client: DummyTradeClient, league: str, logger=None) -> None:
        self.name = name
        self.client = client
        self.league = league
        self.logger = logger
        DummyTradeSource.instances.append(self)


class DummyPriceService:
    instances: List["DummyPriceService"] = []

    def __init__(self, config, parser, db, poe_ninja, trade_source, logger=None) -> None:
        self.config = config
        self.parser = parser
        self.db = db
        self.poe_ninja = poe_ninja
        self.trade_source = trade_source
        self.logger = logger
        DummyPriceService.instances.append(self)


class DummyExistingAdapter:
    instances: List["DummyExistingAdapter"] = []

    def __init__(self, name: str, service: DummyPriceService) -> None:
        self.name = name
        self.service = service
        DummyExistingAdapter.instances.append(self)

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        return []


class DummyUndercutSource:
    instances: List["DummyUndercutSource"] = []

    def __init__(self, name: str, base_service: DummyPriceService, undercut_factor: float) -> None:
        self.name = name
        self.base_service = base_service
        self.undercut_factor = undercut_factor
        DummyUndercutSource.instances.append(self)

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        return []


class DummyMultiSourcePriceService:
    instances: List["DummyMultiSourcePriceService"] = []

    def __init__(self, sources: list[Any]) -> None:
        self.sources = sources
        DummyMultiSourcePriceService.instances.append(self)

    def check_item(self, item_text: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for src in self.sources:
            rows.extend(src.check_item(item_text))
        return rows


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

def test_app_context_uses_config_league_when_auto_detect_disabled(monkeypatch):
    DummyPoeNinja.instances.clear()
    DummyTradeClient.instances.clear()
    DummyTradeSource.instances.clear()
    DummyPriceService.instances.clear()
    DummyExistingAdapter.instances.clear()
    DummyUndercutSource.instances.clear()
    DummyMultiSourcePriceService.instances.clear()

    cfg = DummyConfig()
    cfg.auto_detect_league = False

    # Monkeypatch constructors
    monkeypatch.setattr(appctx, "Config", lambda: cfg)
    monkeypatch.setattr(appctx, "Database", DummyDatabase)
    monkeypatch.setattr(appctx, "PoeNinjaAPI", DummyPoeNinja)
    monkeypatch.setattr(appctx, "PoeTradeClient", DummyTradeClient)
    monkeypatch.setattr(appctx, "TradeApiSource", DummyTradeSource)
    monkeypatch.setattr(appctx, "PriceService", DummyPriceService)
    monkeypatch.setattr(appctx, "ExistingServiceAdapter", DummyExistingAdapter)
    monkeypatch.setattr(appctx, "UndercutPriceSource", DummyUndercutSource)
    monkeypatch.setattr(appctx, "MultiSourcePriceService", DummyMultiSourcePriceService)

    ctx = appctx.create_app_context()

    # Config should be our DummyConfig instance
    assert ctx.config is cfg
    assert cfg.set_game_config_calls == []

    # PoeNinja created with league "Keepers"
    assert len(DummyPoeNinja.instances) == 1
    ninja = DummyPoeNinja.instances[0]
    assert ninja.league == "Keepers"
    assert ninja.detect_calls == 0  # auto-detect disabled

    # Trade client + source use the same league
    assert len(DummyTradeClient.instances) == 1
    client = DummyTradeClient.instances[0]
    assert client.league == "Keepers"

    assert len(DummyTradeSource.instances) == 1
    src = DummyTradeSource.instances[0]
    assert src.league == "Keepers"
    assert src.client is client

    # Price service + multi-source wrapper constructed
    assert len(DummyPriceService.instances) == 1
    ps = DummyPriceService.instances[0]
    assert ps.config is cfg
    assert ps.poe_ninja is ninja
    assert ps.trade_source is src

    assert len(DummyMultiSourcePriceService.instances) == 1
    ms = DummyMultiSourcePriceService.instances[0]
    assert ctx.price_service is ms


def test_app_context_auto_detect_updates_config_and_client_league(monkeypatch):
    DummyPoeNinja.instances.clear()
    DummyTradeClient.instances.clear()
    DummyTradeSource.instances.clear()
    DummyPriceService.instances.clear()
    DummyExistingAdapter.instances.clear()
    DummyUndercutSource.instances.clear()
    DummyMultiSourcePriceService.instances.clear()

    cfg = DummyConfig()
    cfg.auto_detect_league = True

    # Monkeypatch constructors
    monkeypatch.setattr(appctx, "Config", lambda: cfg)
    monkeypatch.setattr(appctx, "Database", DummyDatabase)
    monkeypatch.setattr(appctx, "PoeNinjaAPI", DummyPoeNinja)
    monkeypatch.setattr(appctx, "PoeTradeClient", DummyTradeClient)
    monkeypatch.setattr(appctx, "TradeApiSource", DummyTradeSource)
    monkeypatch.setattr(appctx, "PriceService", DummyPriceService)
    monkeypatch.setattr(appctx, "ExistingServiceAdapter", DummyExistingAdapter)
    monkeypatch.setattr(appctx, "UndercutPriceSource", DummyUndercutSource)
    monkeypatch.setattr(appctx, "MultiSourcePriceService", DummyMultiSourcePriceService)

    # When PoeNinja.detect_current_league is called, it should return a different league
    detected_league = "Detected League"

    # prime behavior after construction
    def _after_construct():
        assert len(DummyPoeNinja.instances) == 1
        DummyPoeNinja.instances[0].detect_result = detected_league

    # Hook into PoeNinja creation to set detect_result before create_app_context uses it
    orig_poe_ninja_ctor = DummyPoeNinja

    def _ctor_with_setup(league: str):
        inst = orig_poe_ninja_ctor(league)
        inst.detect_result = detected_league
        return inst

    monkeypatch.setattr(appctx, "PoeNinjaAPI", _ctor_with_setup)

    ctx = appctx.create_app_context()

    # PoeNinja should now have league updated to detected one
    assert len(DummyPoeNinja.instances) == 1
    ninja = DummyPoeNinja.instances[0]
    assert ninja.detect_calls == 1
    assert ninja.league == detected_league

    # Config.set_game_config should have been called with updated league
    assert len(cfg.set_game_config_calls) == 1
    updated_cfg = cfg.set_game_config_calls[0]
    assert updated_cfg.league == detected_league

    # Trade client / source should also use the detected league
    client = DummyTradeClient.instances[0]
    src = DummyTradeSource.instances[0]
    assert client.league == detected_league
    assert src.league == detected_league
    assert ctx.config is cfg
