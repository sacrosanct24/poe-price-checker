"""Tests for price check endpoints."""

from fastapi.testclient import TestClient
from unittest.mock import MagicMock


class TestPriceCheckEndpoint:
    """Tests for POST /api/v1/price-check."""

    def test_price_check_success(self, client: TestClient):
        """Price check returns valid response."""
        response = client.post(
            "/api/v1/price-check",
            json={
                "item_text": "Rarity: Unique\nHeadhunter\nLeather Belt",
                "game_version": "poe1",
                "league": "Standard",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["item"]["name"] == "Headhunter"
        assert len(data["prices"]) > 0
        assert data["best_price"] is not None

    def test_price_check_minimal_request(self, client: TestClient):
        """Price check works with minimal request."""
        response = client.post(
            "/api/v1/price-check",
            json={"item_text": "Rarity: Unique\nHeadhunter"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_price_check_empty_text_fails(self, client: TestClient):
        """Price check rejects empty item text."""
        response = client.post(
            "/api/v1/price-check",
            json={"item_text": ""},
        )
        assert response.status_code == 422  # Validation error

    def test_price_check_parse_failure(
        self, client: TestClient, mock_app_context: MagicMock
    ):
        """Price check handles parse failures gracefully."""
        mock_app_context.item_parser.parse.return_value = None

        response = client.post(
            "/api/v1/price-check",
            json={"item_text": "invalid item data"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "parse" in data["error"].lower()


class TestParseItemEndpoint:
    """Tests for POST /api/v1/parse-item."""

    def test_parse_item_success(self, client: TestClient):
        """Parse item returns item info."""
        response = client.post(
            "/api/v1/parse-item",
            json={"item_text": "Rarity: Unique\nHeadhunter\nLeather Belt"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Headhunter"
        assert data["base_type"] == "Leather Belt"
        assert data["rarity"] == "unique"

    def test_parse_item_failure(
        self, client: TestClient, mock_app_context: MagicMock
    ):
        """Parse item returns 400 on failure."""
        mock_app_context.item_parser.parse.return_value = None

        response = client.post(
            "/api/v1/parse-item",
            json={"item_text": "invalid"},
        )
        assert response.status_code == 400
