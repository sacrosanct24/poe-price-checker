# tests/test_poeninja_leagues.py

import types
import pytest

from data_sources.pricing.poe_ninja import PoeNinjaAPI



class DummyResponse:
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")

    def json(self):
        return self._json


def test_get_current_leagues_pc_only_and_dedup(monkeypatch):
    # Fake result from trade API: three realms, repeated ids
    fake_json = {
        "result": [
            {"id": "Standard", "text": "Standard", "realm": "pc"},
            {"id": "Standard", "text": "Standard", "realm": "xbox"},
            {"id": "Hardcore", "text": "Hardcore", "realm": "pc"},
            {"id": "Keepers", "text": "Keepers of the Trove", "realm": "pc"},
            {"id": "Keepers", "text": "Keepers of the Trove", "realm": "sony"},
        ]
    }

    def fake_get(url, headers=None, timeout=10):
        return DummyResponse(fake_json)

    import requests
    monkeypatch.setattr(requests, "get", fake_get)

    api = PoeNinjaAPI(league="Standard")
    leagues = api.get_current_leagues()

    ids = {l["name"] for l in leagues}
    assert ids == {"Standard", "Hardcore", "Keepers"}


def test_get_current_leagues_fallback_on_error(monkeypatch):
    import requests

    def fake_get(url, headers=None, timeout=10):
        raise requests.RequestException("Network broken")

    monkeypatch.setattr(requests, "get", fake_get)

    api = PoeNinjaAPI(league="Standard")
    leagues = api.get_current_leagues()

    ids = {l["name"] for l in leagues}
    assert ids == {"Standard", "Hardcore"}
