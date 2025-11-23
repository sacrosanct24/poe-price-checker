from __future__ import annotations

import pytest
from data_sources.pricing.poe_ninja import PoeNinjaAPI

pytestmark = pytest.mark.unit


# ------------------------------------------
# Fake session for mocking Poe Ninja league API
# ------------------------------------------

class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, headers=None, timeout=10):
        self.calls.append(url)

        class R:
            status_code = 200

            def __init__(self, data): self.data = data
            def raise_for_status(self): pass
            def json(self): return self.data

        return R(self.payload)


# ------------------------------------------
# Tests for league retrieval
# ------------------------------------------

def test_get_current_leagues_returns_pc_realms_only():
    payload = {
        "result": [
            {"id": "Standard", "text": "Standard", "realm": "pc"},
            {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
            {"id": "SSF Standard", "text": "SSF Standard", "realm": "pc"},
            {"id": "Xbox League", "text": "Xbox League", "realm": "xbox"},
        ]
    }

    fake = FakeSession(payload)
    api = PoeNinjaAPI(league="Standard")
    api.session = fake

    leagues = api.get_current_leagues()

    assert len(leagues) == 3
    names = {l["name"] for l in leagues}
    assert "Standard" in names
    assert "Hardcore" in names
    assert "SSF Standard" in names
    assert "Xbox League" not in names


def test_detect_current_league_prefers_first_temp_league():
    payload = {
        "result": [
            {"id": "Standard", "text": "Standard", "realm": "pc"},
            {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
            {"id": "Settlers", "text": "Settlers", "realm": "pc"},
            {"id": "HC Settlers", "text": "HC Settlers", "realm": "pc"},
        ]
    }

    fake = FakeSession(payload)
    api = PoeNinjaAPI(league="Standard")
    api.session = fake

    detected = api.detect_current_league()
    assert detected == "Settlers"


def test_detect_current_league_falls_back_to_standard():
    payload = {
        "result": [
            {"id": "Standard", "text": "Standard", "realm": "pc"},
            {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
        ]
    }

    fake = FakeSession(payload)
    api = PoeNinjaAPI(league="Standard")
    api.session = fake

    detected = api.detect_current_league()
    assert detected == "Standard"
