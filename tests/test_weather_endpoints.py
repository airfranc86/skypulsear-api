"""Tests para endpoints de weather."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_get_current_weather(
    client: TestClient, cordoba_coords: dict[str, float]
) -> None:
    """Test del endpoint GET /api/v1/weather/current."""
    response = client.get(
        "/api/v1/weather/current",
        params={"lat": cordoba_coords["lat"], "lon": cordoba_coords["lon"]},
    )

    # Puede retornar 200 (éxito) o 503 (servicio no disponible)
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert "location" in data
        assert "timestamp" in data
        assert "confidence" in data
        assert "sources" in data
        assert data["location"]["lat"] == cordoba_coords["lat"]
        assert data["location"]["lon"] == cordoba_coords["lon"]
        assert 0 <= data["confidence"] <= 1


@pytest.mark.integration
def test_get_current_weather_invalid_coords(client: TestClient) -> None:
    """Test del endpoint con coordenadas inválidas."""
    # Latitud fuera de rango
    response = client.get(
        "/api/v1/weather/current",
        params={"lat": 100, "lon": 0},
    )
    assert response.status_code == 422  # Validation error

    # Longitud fuera de rango
    response = client.get(
        "/api/v1/weather/current",
        params={"lat": 0, "lon": 200},
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_get_forecast(client: TestClient, cordoba_coords: dict[str, float]) -> None:
    """Test del endpoint GET /api/v1/weather/forecast."""
    response = client.get(
        "/api/v1/weather/forecast",
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
        assert "hours" in data
        assert "forecast" in data
        assert "confidence" in data
        assert "sources" in data
        assert data["hours"] == 24
        assert isinstance(data["forecast"], list)
        assert 0 <= data["confidence"] <= 1


@pytest.mark.integration
def test_get_forecast_invalid_hours(
    client: TestClient, cordoba_coords: dict[str, float]
) -> None:
    """Test del endpoint con horas inválidas."""
    # Horas fuera de rango
    response = client.get(
        "/api/v1/weather/forecast",
        params={
            "lat": cordoba_coords["lat"],
            "lon": cordoba_coords["lon"],
            "hours": 200,  # Máximo es 168
        },
    )
    assert response.status_code == 422

    # Horas negativas
    response = client.get(
        "/api/v1/weather/forecast",
        params={
            "lat": cordoba_coords["lat"],
            "lon": cordoba_coords["lon"],
            "hours": -1,
        },
    )
    assert response.status_code == 422
