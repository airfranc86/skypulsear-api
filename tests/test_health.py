"""Tests para endpoint de health check."""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    """Test del endpoint /health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "skypulse-api"


def test_root_endpoint(client: TestClient) -> None:
    """Test del endpoint raíz."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SkyPulse API"
    assert data["version"] == "2.0.0"
    assert "docs" in data
    assert "health" in data
