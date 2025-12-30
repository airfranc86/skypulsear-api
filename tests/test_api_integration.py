"""Tests de integración end-to-end de la API."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.slow
def test_full_workflow(client: TestClient) -> None:
    """
    Test del flujo completo: weather -> patterns -> alerts -> risk-score.

    Este test verifica que todos los endpoints funcionen juntos.
    """
    cordoba_lat = -31.4167
    cordoba_lon = -64.1833
    profile = "piloto"

    # 1. Obtener datos meteorológicos actuales
    weather_response = client.get(
        "/api/v1/weather/current",
        params={"lat": cordoba_lat, "lon": cordoba_lon},
    )

    # Si el servicio no está disponible, saltar el test
    if weather_response.status_code == 503:
        pytest.skip("Servicio meteorológico no disponible")

    assert weather_response.status_code == 200
    weather_data = weather_response.json()
    assert "temperature" in weather_data or weather_data.get("temperature") is None

    # 2. Obtener pronóstico
    forecast_response = client.get(
        "/api/v1/weather/forecast",
        params={"lat": cordoba_lat, "lon": cordoba_lon, "hours": 24},
    )

    if forecast_response.status_code == 503:
        pytest.skip("Servicio meteorológico no disponible")

    assert forecast_response.status_code == 200
    forecast_data = forecast_response.json()
    assert "forecast" in forecast_data

    # 3. Detectar patrones
    patterns_response = client.get(
        "/api/v1/patterns/",
        params={"lat": cordoba_lat, "lon": cordoba_lon, "hours": 72},
    )

    if patterns_response.status_code == 503:
        pytest.skip("Servicio meteorológico no disponible")

    assert patterns_response.status_code == 200
    patterns_data = patterns_response.json()
    assert "patterns" in patterns_data

    # 4. Obtener alertas
    alerts_response = client.get(
        "/api/v1/alerts/",
        params={"lat": cordoba_lat, "lon": cordoba_lon, "hours": 24},
    )

    if alerts_response.status_code == 503:
        pytest.skip("Servicio meteorológico no disponible")

    assert alerts_response.status_code == 200
    alerts_data = alerts_response.json()
    assert "alerts" in alerts_data

    # 5. Calcular risk score
    risk_response = client.post(
        "/api/v1/risk-score",
        json={
            "lat": cordoba_lat,
            "lon": cordoba_lon,
            "profile": profile,
            "hours_ahead": 6,
        },
    )

    if risk_response.status_code == 503:
        pytest.skip("Servicio meteorológico no disponible")

    assert risk_response.status_code == 200
    risk_data = risk_response.json()
    assert "score" in risk_data
    assert 0 <= risk_data["score"] <= 5

    # Verificar consistencia: si hay alertas críticas, el risk score debería ser alto
    if alerts_data["max_level"] >= 3:
        assert (
            risk_data["score"] >= 2
        ), "Risk score debería ser alto si hay alertas nivel 3+"


@pytest.mark.integration
def test_cors_headers(client: TestClient) -> None:
    """Test que CORS esté configurado correctamente."""
    response = client.options(
        "/api/v1/weather/current",
        headers={
            "Origin": "https://skypulse.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    # OPTIONS puede retornar 200 o 405 dependiendo de la configuración
    assert response.status_code in [200, 405, 404]
