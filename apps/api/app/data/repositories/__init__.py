"""Repositorios de datos para SkyPulse.

Solo Windy y AWS WRF-SMN están disponibles.
"""

from app.data.repositories.base_repository import IWeatherRepository
from app.data.repositories.windy_repository import WindyRepository

# Importación condicional de WRFSMNRepository (requiere boto3, s3fs, xarray)
try:
    from app.data.repositories.wrfsmn_repository import WRFSMNRepository

    WRFSMN_AVAILABLE = True
except ImportError as e:
    # boto3, s3fs o xarray no están instalados
    WRFSMN_AVAILABLE = False
    WRFSMNRepository = None  # type: ignore

__all__ = [
    "IWeatherRepository",
    "WindyRepository",
]

if WRFSMN_AVAILABLE:
    __all__.append("WRFSMNRepository")
