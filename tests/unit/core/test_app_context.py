from __future__ import annotations

import pytest

from core.app_context import create_app_context
from core.game_version import GameVersion

pytestmark = pytest.mark.unit


def test_create_app_context_smoke() -> None:
    """
    Basic wiring smoke test: ensures create_app_context returns an object with
    the expected key components. This catches accidental breakage in DI wiring.
    """
    ctx = create_app_context()

    assert ctx.config is not None
    assert ctx.parser is not None
    assert ctx.db is not None
    assert ctx.poe_ninja is not None
    assert ctx.price_service is not None

    assert ctx.config.game_version in (GameVersion.POE1, GameVersion.POE2)
