"""
Tests de integración para POST /api/v1/risk-score.

Verifica contrato de respuesta: score y sub-scores en escala 0-5,
perfil ignorado (siempre general).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    """App FastAPI para tests."""
    from app.api.main import app as _app
    return _app


@pytest_asyncio.fixture
async def client(app):
    """Cliente HTTP asíncrono contra la app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_post_risk_score_returns_200_and_contract(
    client: AsyncClient,
    test_api_key: str,
    sample_coordinates: dict[str, float],
    mock_env_vars: None,
) -> None:
    """POST /risk-score con body válido devuelve 200 y scores en 0-5."""
    response = await client.post(
        "/api/v1/risk-score",
        json={
            "lat": sample_coordinates["lat"],
            "lon": sample_coordinates["lon"],
            "profile": "general",
            "hours_ahead": 6,
        },
        headers={"x-api-key": test_api_key},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "score" in data
    assert 0 <= data["score"] <= 5
    for key in (
        "temperature_risk",
        "wind_risk",
        "precipitation_risk",
        "storm_risk",
        "hail_risk",
        "pattern_risk",
        "alert_risk",
    ):
        assert key in data, f"Falta campo {key}"
        assert 0 <= data[key] <= 5, f"{key} debe estar en [0, 5], obtuvo {data[key]}"
    assert "category" in data
    assert isinstance(data["category"], str)


@pytest.mark.asyncio
async def test_post_risk_score_accepts_optional_profile(
    client: AsyncClient,
    test_api_key: str,
    sample_coordinates: dict[str, float],
    mock_env_vars: None,
) -> None:
    """POST /risk-score acepta profile opcional (se ignora; siempre general)."""
    response = await client.post(
        "/api/v1/risk-score",
        json={
            "lat": sample_coordinates["lat"],
            "lon": sample_coordinates["lon"],
            "hours_ahead": 6,
        },
        headers={"x-api-key": test_api_key},
    )
    # Puede ser 200 (datos) o 503 (servicio no disponible)
    assert response.status_code in (200, 503), response.text
    if response.status_code == 200:
        data = response.json()
        assert 0 <= data["score"] <= 5


@pytest.mark.asyncio
async def test_post_risk_score_requires_api_key(
    client: AsyncClient,
    sample_coordinates: dict[str, float],
) -> None:
    """POST /risk-score sin API key devuelve 401."""
    response = await client.post(
        "/api/v1/risk-score",
        json={
            "lat": sample_coordinates["lat"],
            "lon": sample_coordinates["lon"],
            "profile": "general",
            "hours_ahead": 6,
        },
    )
    assert response.status_code == 401, response.text
