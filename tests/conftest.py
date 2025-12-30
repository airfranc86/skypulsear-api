"""Configuración compartida para tests."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app


@pytest.fixture
def client() -> TestClient:
    """Cliente de prueba para la API."""
    return TestClient(app)


@pytest.fixture
def cordoba_coords() -> dict[str, float]:
    """Coordenadas de Córdoba, Argentina."""
    return {"lat": -31.4167, "lon": -64.1833}


@pytest.fixture
def valid_profile() -> str:
    """Perfil válido para testing."""
    return "piloto"
