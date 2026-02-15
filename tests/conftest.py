"""
Configuración compartida de pytest para SkyPulse.
Fixtures y configuración común para todos los tests.
"""

import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
from dotenv import load_dotenv
from httpx import AsyncClient

# Agregar apps/api al PYTHONPATH para imports
project_root = Path(__file__).parent.parent
api_path = project_root / "apps" / "api"
sys.path.insert(0, str(api_path))

# Cargar variables de entorno de test
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

# Configurar variables de entorno de test si no existen
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("VALID_API_KEYS", "demo-key,test-key-123")
os.environ.setdefault("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def test_api_key() -> str:
    """API key válida para tests."""
    return "demo-key"


@pytest.fixture(scope="session")
def invalid_api_key() -> str:
    """API key inválida para tests."""
    return "invalid-key-12345"


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP asíncrono para tests de API.
    
    Nota: Requiere que el servidor esté corriendo en localhost:8000
    Para tests de integración.
    """
    from app.api.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture para mockear variables de entorno."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("VALID_API_KEYS", "demo-key,test-key-123")
    monkeypatch.setenv("WINDY_POINT_FORECAST_API_KEY", "test-windy-key")


@pytest.fixture(scope="function")
def sample_coordinates() -> dict[str, float]:
    """Coordenadas de ejemplo (Córdoba, Argentina)."""
    return {
        "lat": -31.4201,
        "lon": -64.1888
    }


@pytest.fixture(scope="function")
def sample_weather_data() -> dict:
    """Datos meteorológicos de ejemplo."""
    return {
        "temperature": 22.5,
        "humidity": 65,
        "wind_speed": 12.0,
        "wind_direction": 180,
        "pressure": 1013.25,
        "precipitation": 0.0,
        "cloud_cover": 45
    }
