"""Tests para endpoints de alertas."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_get_alerts(client: TestClient, cordoba_coords: dict[str, float]) -> None:
    """Test del endpoint GET /api/v1/alerts."""
    response = client.get(
        "/api/v1/alerts/",
        params={
            "lat": cordoba_coords["lat"],
            "lon": cordoba_coords["lon"],
            "hours": 24,
        },
    )

    # Puede retornar 200 (éxito) o 503 (servicio no disponible)
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert "location" in data
        assert "alerts" in data
        assert "alert_count" in data
        assert "max_level" in data
        assert "max_level_name" in data
        assert isinstance(data["alerts"], list)
        assert 0 <= data["max_level"] <= 4
        assert data["alert_count"] == len(data["alerts"])


@pytest.mark.integration
def test_get_alerts_invalid_coords(client: TestClient) -> None:
    """Test del endpoint con coordenadas inválidas."""
    response = client.get(
        "/api/v1/alerts/",
        params={"lat": 100, "lon": 0, "hours": 24},
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_get_alerts_invalid_hours(
    client: TestClient, cordoba_coords: dict[str, float]
) -> None:
    """Test del endpoint con horas inválidas."""
    response = client.get(
        "/api/v1/alerts/",
        params={
            "lat": cordoba_coords["lat"],
            "lon": cordoba_coords["lon"],
            "hours": 200,  # Máximo es 72
        },
    )
    assert response.status_code == 422
