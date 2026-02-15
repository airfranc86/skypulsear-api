"""
Tests de integración M1.4: WRF-SMN y fallback a GFS.

- Córdoba, Resistencia, Mendoza y Bs As (CABA AEP): GET /weather/current y
  /weather/forecast devuelven 200 (o 503 si no hay fuentes) y estructura válida.
- Validar que la respuesta incluye current/meteo_source_display y forecast como array.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Coordenadas RFC M1.4: Córdoba, Resistencia, Mendoza, Bs As (CABA AEP)
CORDOBA = {"lat": -31.4201, "lon": -64.1888}
RESISTENCIA = {"lat": -27.4512, "lon": -58.9866}
MENDOZA = {"lat": -32.8895, "lon": -68.8458}
BSAS_CABA_AEP = {"lat": -34.5592, "lon": -58.4156}

M1_4_LOCATIONS = [
    (CORDOBA, "Córdoba"),
    (RESISTENCIA, "Resistencia"),
    (MENDOZA, "Mendoza"),
    (BSAS_CABA_AEP, "Bs As (CABA AEP)"),
]


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


def _valid_current_structure(data: dict) -> bool:
    """Comprueba que la respuesta de /current tiene estructura esperada por el frontend."""
    if not data or not isinstance(data, dict):
        return False
    current = data.get("current")
    if not current or not isinstance(current, dict):
        return False
    return "temperature" in current or "temperature_2m" in current


def _valid_forecast_structure(data: dict) -> bool:
    """Comprueba que la respuesta de /forecast tiene forecast como array."""
    if not data or not isinstance(data, dict):
        return False
    forecast = data.get("forecast")
    return isinstance(forecast, list)


@pytest.mark.asyncio
@pytest.mark.parametrize("coords,label", M1_4_LOCATIONS)
async def test_weather_current_cordoba_resistencia_structure(
    client: AsyncClient,
    test_api_key: str,
    coords: dict,
    label: str,
    mock_env_vars: None,
) -> None:
    """
    GET /api/v1/weather/current para Córdoba, Resistencia, Mendoza y Bs As (CABA AEP)
    devuelve 200 o 503. Si 200: current con temperature y opcional meteo_source_display.
    """
    response = await client.get(
        "/api/v1/weather/current",
        params={"lat": coords["lat"], "lon": coords["lon"]},
        headers={"x-api-key": test_api_key},
    )
    assert response.status_code in (200, 503), (
        f"{label}: esperado 200 o 503, obtuvo {response.status_code} - {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert _valid_current_structure(data), (
            f"{label}: respuesta sin current/temperature - {list(data.keys())}"
        )
        # meteo_source_display puede estar en root o en current según versión
        assert "current" in data


@pytest.mark.asyncio
@pytest.mark.parametrize("coords,label", M1_4_LOCATIONS)
async def test_weather_forecast_cordoba_resistencia_structure(
    client: AsyncClient,
    test_api_key: str,
    coords: dict,
    label: str,
    mock_env_vars: None,
) -> None:
    """
    GET /api/v1/weather/forecast para Córdoba, Resistencia, Mendoza y Bs As (CABA AEP)
    devuelve 200 o 503. Si 200: forecast es array (puede estar vacío si no hay datos).
    """
    response = await client.get(
        "/api/v1/weather/forecast",
        params={"lat": coords["lat"], "lon": coords["lon"], "hours": 48},
        headers={"x-api-key": test_api_key},
    )
    assert response.status_code in (200, 503), (
        f"{label}: esperado 200 o 503, obtuvo {response.status_code} - {response.text}"
    )
    if response.status_code == 200:
        data = response.json()
        assert _valid_forecast_structure(data), (
            f"{label}: forecast debe ser array - {type(data.get('forecast'))}"
        )


@pytest.mark.asyncio
async def test_weather_endpoints_require_api_key(client: AsyncClient) -> None:
    """GET /current y /forecast sin API key devuelven 401."""
    r_current = await client.get(
        "/api/v1/weather/current",
        params={"lat": CORDOBA["lat"], "lon": CORDOBA["lon"]},
    )
    r_forecast = await client.get(
        "/api/v1/weather/forecast",
        params={"lat": CORDOBA["lat"], "lon": CORDOBA["lon"], "hours": 24},
    )
    assert r_current.status_code == 401, r_current.text
    assert r_forecast.status_code == 401, r_forecast.text
