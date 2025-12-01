"""Tests for sales endpoints."""

from fastapi.testclient import TestClient


class TestSalesListEndpoint:
    """Tests for GET /api/v1/sales."""

    def test_list_sales_success(self, client: TestClient):
        """List sales returns paginated results."""
        response = client.get("/api/v1/sales")
        assert response.status_code == 200

        data = response.json()
        assert "sales" in data
        assert "total" in data
        assert len(data["sales"]) == 2  # From mock

    def test_list_sales_filter_pending(self, client: TestClient):
        """List sales filters pending sales."""
        response = client.get("/api/v1/sales?status=pending")
        assert response.status_code == 200

        data = response.json()
        for sale in data["sales"]:
            assert sale["sold_at"] is None

    def test_list_sales_filter_completed(self, client: TestClient):
        """List sales filters completed sales."""
        response = client.get("/api/v1/sales?status=completed")
        assert response.status_code == 200

        data = response.json()
        for sale in data["sales"]:
            assert sale["sold_at"] is not None


class TestCreateSaleEndpoint:
    """Tests for POST /api/v1/sales."""

    def test_create_sale_success(self, client: TestClient):
        """Create sale returns new sale."""
        response = client.post(
            "/api/v1/sales",
            json={
                "item_name": "Mageblood",
                "listed_price_chaos": 50000.0,
                "notes": "Testing",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["item_name"] == "Mageblood"
        assert data["listed_price_chaos"] == 50000.0
        assert data["notes"] == "Testing"
        assert data["sold_at"] is None

    def test_create_sale_minimal(self, client: TestClient):
        """Create sale works with minimal data."""
        response = client.post(
            "/api/v1/sales",
            json={
                "item_name": "Chaos Orb",
                "listed_price_chaos": 1.0,
            },
        )
        assert response.status_code == 201

    def test_create_sale_invalid_price(self, client: TestClient):
        """Create sale rejects invalid price."""
        response = client.post(
            "/api/v1/sales",
            json={
                "item_name": "Test",
                "listed_price_chaos": -10.0,
            },
        )
        assert response.status_code == 422


class TestSaleDetailEndpoint:
    """Tests for GET /api/v1/sales/{sale_id}."""

    def test_get_sale_success(self, client: TestClient):
        """Get sale returns sale details."""
        response = client.get("/api/v1/sales/1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == 1
        assert data["item_name"] == "Tabula Rasa"

    def test_get_sale_not_found(self, client: TestClient):
        """Get sale returns 404 for unknown ID."""
        response = client.get("/api/v1/sales/9999")
        assert response.status_code == 404


class TestUpdateSaleEndpoint:
    """Tests for PUT /api/v1/sales/{sale_id}."""

    def test_update_sale_mark_sold(self, client: TestClient):
        """Update sale can mark as sold."""
        response = client.put(
            "/api/v1/sales/2",
            json={"actual_price_chaos": 6.0},
        )
        assert response.status_code == 200


class TestInstantSaleEndpoint:
    """Tests for POST /api/v1/sales/instant."""

    def test_instant_sale_success(self, client: TestClient):
        """Instant sale records immediate sale."""
        response = client.post(
            "/api/v1/sales/instant",
            json={
                "item_name": "Divine Orb",
                "listed_price_chaos": 180.0,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["item_name"] == "Divine Orb"
        assert data["sold_at"] is not None
        assert data["time_to_sale_hours"] == 0
