"""Tests for items endpoints."""

from fastapi.testclient import TestClient


class TestItemsListEndpoint:
    """Tests for GET /api/v1/items."""

    def test_list_items_success(self, client: TestClient):
        """List items returns paginated results."""
        response = client.get("/api/v1/items")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["items"]) == 2  # From mock

    def test_list_items_with_pagination(self, client: TestClient):
        """List items respects pagination parameters."""
        response = client.get("/api/v1/items?limit=1&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert len(data["items"]) == 1

    def test_list_items_filter_by_game_version(self, client: TestClient):
        """List items filters by game version."""
        response = client.get("/api/v1/items?game_version=poe1")
        assert response.status_code == 200
        assert response.json()["total"] >= 0

    def test_list_items_filter_by_league(self, client: TestClient):
        """List items filters by league."""
        response = client.get("/api/v1/items?league=Standard")
        assert response.status_code == 200

    def test_list_items_search(self, client: TestClient):
        """List items supports search."""
        response = client.get("/api/v1/items?search=headhunter")
        assert response.status_code == 200

        data = response.json()
        for item in data["items"]:
            assert "headhunter" in item["item_name"].lower()


class TestItemDetailEndpoint:
    """Tests for GET /api/v1/items/{item_id}."""

    def test_get_item_success(self, client: TestClient):
        """Get item returns item details."""
        response = client.get("/api/v1/items/1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == 1
        assert data["item_name"] == "Headhunter"

    def test_get_item_not_found(self, client: TestClient):
        """Get item returns 404 for unknown ID."""
        response = client.get("/api/v1/items/9999")
        assert response.status_code == 404
