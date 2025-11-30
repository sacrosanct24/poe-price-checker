"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for /health endpoints."""

    def test_health_check_success(self, client: TestClient):
        """Health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["database"] == "connected"
        assert "services" in data

    def test_readiness_check(self, client: TestClient):
        """Readiness probe returns ready."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_liveness_check(self, client: TestClient):
        """Liveness probe returns alive."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_config_endpoint(self, client: TestClient):
        """Config endpoint returns current config."""
        response = client.get("/config")
        assert response.status_code == 200

        data = response.json()
        assert "game_version" in data
        assert "league" in data
        assert data["league"] == "Standard"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_info(self, client: TestClient):
        """Root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert data["docs"] == "/docs"
