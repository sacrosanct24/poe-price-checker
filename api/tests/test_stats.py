"""Tests for statistics endpoints."""

from fastapi.testclient import TestClient


class TestStatsEndpoint:
    """Tests for GET /api/v1/stats."""

    def test_get_stats_success(self, client: TestClient):
        """Get stats returns aggregated data."""
        response = client.get("/api/v1/stats")
        assert response.status_code == 200

        data = response.json()
        assert "period_days" in data
        assert "total_items_checked" in data
        assert "total_sales" in data
        assert "total_chaos_earned" in data
        assert data["period_days"] == 30  # Default

    def test_get_stats_custom_period(self, client: TestClient):
        """Get stats respects custom period."""
        response = client.get("/api/v1/stats?days=7")
        assert response.status_code == 200
        assert response.json()["period_days"] == 7

    def test_get_stats_invalid_period(self, client: TestClient):
        """Get stats rejects invalid period."""
        response = client.get("/api/v1/stats?days=0")
        assert response.status_code == 422

        response = client.get("/api/v1/stats?days=1000")
        assert response.status_code == 422


class TestStatsSummaryEndpoint:
    """Tests for GET /api/v1/stats/summary."""

    def test_get_summary_success(self, client: TestClient):
        """Get summary returns quick metrics."""
        response = client.get("/api/v1/stats/summary")
        assert response.status_code == 200

        data = response.json()
        assert "items_checked_today" in data
        assert "sales_completed_today" in data
        assert "pending_sales" in data
        assert "timestamp" in data
