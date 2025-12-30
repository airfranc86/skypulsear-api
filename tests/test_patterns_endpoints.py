"""Tests para endpoints de patrones."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_get_patterns(client: TestClient, cordoba_coords: dict[str, float]) -> None:
    """Test del endpoint GET /api/v1/patterns."""
    response = client.get(
        "/api/v1/patterns/",
        params={
            "lat": cordoba_coords["lat"],
            "lon": cordoba_coords["lon"],
            "hours": 72,
        },
    )

    # Puede retornar 200 (éxito) o 503 (servicio no disponible)
    assert response.status_code in [200, 503]

    if response.status_code == 200:
        data = response.json()
        assert "location" in data
        assert "patterns" in data
        assert "pattern_count" in data
        assert "max_risk_level" in data
        assert isinstance(data["patterns"], list)
        assert data["pattern_count"] == len(data["patterns"])

        # Si hay patrones, verificar estructura
        if data["patterns"]:
            pattern = data["patterns"][0]
            assert "pattern_type" in pattern
            assert "risk_level" in pattern
            assert "confidence" in pattern
            assert "title" in pattern
            assert "description" in pattern
            assert 0 <= pattern["confidence"] <= 1


@pytest.mark.integration
def test_get_pattern_types(client: TestClient) -> None:
    """Test del endpoint GET /api/v1/patterns/types."""
    response = client.get("/api/v1/patterns/types")
    assert response.status_code == 200
    data = response.json()
    assert "patterns" in data
    assert isinstance(data["patterns"], list)
    assert len(data["patterns"]) > 0

    # Verificar estructura de cada patrón
    for pattern in data["patterns"]:
        assert "id" in pattern
        assert "name" in pattern
        assert "description" in pattern
        assert "regions" in pattern


@pytest.mark.integration
def test_get_patterns_invalid_coords(client: TestClient) -> None:
    """Test del endpoint con coordenadas inválidas."""
    response = client.get(
        "/api/v1/patterns/",
        params={"lat": 100, "lon": 0, "hours": 72},
    )
    assert response.status_code == 422
