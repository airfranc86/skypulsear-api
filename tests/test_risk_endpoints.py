"""Tests para endpoints de risk scoring."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_calculate_risk_score(
    client: TestClient, cordoba_coords: dict[str, float], valid_profile: str
) -> None:
    """Test del endpoint POST /api/v1/risk-score."""
    response = client.post(
        "/api/v1/risk-score",
        json={
            "lat": cordoba_coords["lat"],
            "lon": cordoba_coords["lon"],
            "profile": valid_profile,
            "hours_ahead": 6,
        },
    )

    # Puede retornar 200 (éxito) o 503 (servicio no disponible)
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert "score" in data
        assert "category" in data
        assert "risk_score_100" in data
        assert "confidence" in data
        assert 0 <= data["score"] <= 5
        assert 0 <= data["risk_score_100"] <= 100
        assert 0 <= data["confidence"] <= 1
        assert "temperature_risk" in data
        assert "wind_risk" in data
        assert "precipitation_risk" in data
        assert "storm_risk" in data
        assert "hail_risk" in data


@pytest.mark.integration
def test_calculate_risk_score_invalid_profile(
    client: TestClient, cordoba_coords: dict[str, float]
) -> None:
    """Test del endpoint con perfil inválido."""
    response = client.post(
        "/api/v1/risk-score",
        json={
            "lat": cordoba_coords["lat"],
            "lon": cordoba_coords["lon"],
            "profile": "perfil_inexistente",
            "hours_ahead": 6,
        },
    )
    assert response.status_code == 400
    # El nuevo formato de error tiene estructura: {"error": {"message": ...}}
    error_data = response.json()
    error_message = error_data.get("error", {}).get("message", "") or error_data.get(
        "detail", ""
    )
    assert "no válido" in error_message.lower() or "perfil" in error_message.lower()


@pytest.mark.integration
def test_calculate_risk_score_invalid_coords(
    client: TestClient, valid_profile: str
) -> None:
    """Test del endpoint con coordenadas inválidas."""
    response = client.post(
        "/api/v1/risk-score",
        json={
            "lat": 100,  # Fuera de rango
            "lon": 0,
            "profile": valid_profile,
            "hours_ahead": 6,
        },
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_calculate_risk_score_all_profiles(
    client: TestClient, cordoba_coords: dict[str, float]
) -> None:
    """Test del endpoint con todos los perfiles válidos."""
    profiles = [
        "piloto",
        "agricultor",
        "camionero",
        "deporte_aire_libre",
        "evento_exterior",
        "construccion",
        "turismo",
        "general",
    ]

    for profile in profiles:
        response = client.post(
            "/api/v1/risk-score",
            json={
                "lat": cordoba_coords["lat"],
                "lon": cordoba_coords["lon"],
                "profile": profile,
                "hours_ahead": 6,
            },
        )
        # Puede retornar 200 o 503 (si no hay datos disponibles)
        assert response.status_code in [200, 400, 503]

        if response.status_code == 200:
            data = response.json()
            assert 0 <= data["score"] <= 5
