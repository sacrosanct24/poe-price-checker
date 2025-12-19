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
    # Note: get_current_leagues() actually calls the real PoE trade API,
    # but for testing we can mock requests. For now, just verify it
    # returns something reasonable or falls back to Standard/Hardcore
    import requests
    from unittest.mock import patch

    mock_payload = {
        "result": [
            {"id": "Standard", "text": "Standard", "realm": "pc"},
            {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
            {"id": "SSF Standard", "text": "SSF Standard", "realm": "pc"},
            {"id": "Keepers", "text": "Keepers of the Trove", "realm": "pc"},
            {"id": "HC Keepers", "text": "HC Keepers of the Trove", "realm": "pc"},
            {"id": "SSF Keepers", "text": "SSF Keepers of the Trove", "realm": "pc"},
            {"id": "HC SSF Keepers", "text": "HC SSF Keepers of the Trove", "realm": "pc"},
            {"id": "XSSF Keepers", "text": "XSSF Keepers of the Trove", "realm": "pc"},
            {"id": "Xbox League", "text": "Xbox League", "realm": "xbox"},
        ]
    }

    class MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return mock_payload

    with patch.object(requests, 'get', return_value=MockResponse()):
        api = PoeNinjaAPI(league="Standard")
        leagues = api.get_current_leagues()

    # Should have 8 PC leagues, not the Xbox one
    assert len(leagues) == 8
    names = {league["name"] for league in leagues}
    assert "Standard" in names
    assert "Hardcore" in names
    assert "Xbox League" not in names


def test_detect_current_league_prefers_first_temp_league():
    import requests
    from unittest.mock import patch

    mock_payload = {
        "result": [
            {"id": "Standard", "text": "Standard", "realm": "pc"},
            {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
            {"id": "Settlers", "text": "Settlers", "realm": "pc"},
            {"id": "HC Settlers", "text": "HC Settlers", "realm": "pc"},
        ]
    }

    class MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return mock_payload

    with patch.object(requests, 'get', return_value=MockResponse()):
        api = PoeNinjaAPI(league="Standard")
        detected = api.detect_current_league()

    assert detected == "Settlers"


def test_detect_current_league_falls_back_to_standard():
    import requests
    from unittest.mock import patch

    mock_payload = {
        "result": [
            {"id": "Standard", "text": "Standard", "realm": "pc"},
            {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
        ]
    }

    class MockResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return mock_payload

    with patch.object(requests, 'get', return_value=MockResponse()):
        api = PoeNinjaAPI(league="Standard")
        detected = api.detect_current_league()

    assert detected == "Standard"
