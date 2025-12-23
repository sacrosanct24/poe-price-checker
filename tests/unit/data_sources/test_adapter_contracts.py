"""Contract tests for data source adapters using fixture payloads."""

import json

import pytest

from data_sources.poe_ninja_client import PoeNinjaClient
from data_sources.repoe_client import RePoEClient

pytestmark = pytest.mark.unit


@pytest.fixture
def ninja_currency_payload():
    """Fixture payload for poe.ninja currency endpoint."""
    return {
        "lines": [
            {
                "currencyTypeName": "Divine Orb",
                "chaosEquivalent": 240.5,
                "icon": "https://example.com/divine.png",
                "detailsId": "divine-orb",
            }
        ]
    }


@pytest.fixture
def ninja_item_payload():
    """Fixture payload for poe.ninja item endpoint."""
    return {
        "lines": [
            {
                "name": "Mageblood",
                "baseType": "Heavy Belt",
                "chaosValue": 50000,
                "divineValue": 300,
                "variant": "4 Flask",
                "links": 0,
                "icon": "https://example.com/mageblood.png",
                "detailsId": "mageblood",
            }
        ]
    }


@pytest.fixture
def repoe_mods_payload():
    """Fixture payload for RePoE mods data."""
    return {
        "TestLifeMod1": {
            "name": "of Testing",
            "domain": "item",
            "generation_type": "suffix",
            "required_level": 5,
            "stats": [{"id": "maximum_life", "min": 20, "max": 30}],
            "spawn_weights": [{"tag": "ring", "weight": 1000}],
            "groups": ["TestLifeGroup"],
            "implicit_tags": [],
            "is_essence_only": False,
        }
    }


@pytest.fixture
def repoe_base_items_payload():
    """Fixture payload for RePoE base items data."""
    return {
        "Metadata/Items/Rings/Ring1": {
            "name": "Coral Ring",
            "item_class": "Rings",
            "inventory_width": 1,
            "inventory_height": 1,
            "drop_level": 1,
            "tags": ["ring", "default"],
            "implicits": ["LifeImplicit1"],
            "requirements": {},
        }
    }


def test_poe_ninja_currency_contract(monkeypatch, ninja_currency_payload):
    """Currency endpoint maps to NinjaPrice fields."""
    client = PoeNinjaClient()

    def fake_get(endpoint, params=None):
        assert endpoint == client.CURRENCY_URL
        assert params == {"league": "Standard", "type": "Currency"}
        return ninja_currency_payload

    monkeypatch.setattr(client, "get", fake_get)

    prices = client.get_currency_prices("Standard", "Currency")

    assert len(prices) == 1
    price = prices[0]
    assert price.name == "Divine Orb"
    assert price.chaos_value == 240.5
    assert price.item_class == "currency"
    assert price.details_id == "divine-orb"


def test_poe_ninja_item_contract(monkeypatch, ninja_item_payload):
    """Item endpoint maps to NinjaPrice fields."""
    client = PoeNinjaClient()

    def fake_get(endpoint, params=None):
        assert endpoint == client.ITEM_URL
        assert params == {"league": "Standard", "type": "UniqueAccessory"}
        return ninja_item_payload

    monkeypatch.setattr(client, "get", fake_get)

    prices = client.get_item_prices("Standard", "UniqueAccessory")

    assert len(prices) == 1
    price = prices[0]
    assert price.name == "Mageblood"
    assert price.base_type == "Heavy Belt"
    assert price.chaos_value == 50000
    assert price.divine_value == 300
    assert price.variant == "4 Flask"
    assert price.item_class == "UniqueAccessory"
    assert price.details_id == "mageblood"


def test_repoe_client_contract_from_cache(tmp_path, repoe_mods_payload, repoe_base_items_payload):
    """RePoE client reads fixture cache data without network."""
    cache_dir = tmp_path / "repoe_cache"
    cache_dir.mkdir()

    mods_path = cache_dir / "mods.min.json"
    base_items_path = cache_dir / "base_items.min.json"

    mods_path.write_text(json.dumps(repoe_mods_payload), encoding="utf-8")
    base_items_path.write_text(json.dumps(repoe_base_items_payload), encoding="utf-8")

    client = RePoEClient(cache_dir=cache_dir, auto_download=False)

    mods = client.find_mod_by_stat("maximum_life")
    assert len(mods) == 1
    assert mods[0].name == "of Testing"
    assert mods[0].is_suffix is True

    base_item = client.find_base_item("Coral Ring")
    assert base_item is not None
    assert base_item.item_class == "Rings"
