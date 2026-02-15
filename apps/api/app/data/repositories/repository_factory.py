"""Factory para crear repositorios de datos meteorológicos."""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

from app.data.repositories.base_repository import IWeatherRepository
from app.data.repositories.windy_repository import WindyRepository
from app.utils.logging_config import get_logger

# Importación condicional de WRFSMNRepository (requiere boto3, s3fs, xarray)
try:
    from app.data.repositories.wrfsmn_repository import WRFSMNRepository

    WRFSMN_AVAILABLE = True
except ImportError:
    # boto3, s3fs o xarray no están instalados
    WRFSMN_AVAILABLE = False
    WRFSMNRepository = None  # type: ignore

load_dotenv()
logger = get_logger(__name__)


class RepositoryFactory:
    """
    Factory para crear y gestionar repositorios de datos meteorológicos.
    """

    def __init__(self) -> None:
        """Inicializa el factory con todos los repositorios disponibles."""
        self.repositories: Dict[str, IWeatherRepository] = (
            create_all_available_repositories()
        )

    def get_repository(self, source_name: str) -> Optional[IWeatherRepository]:
        """
        Obtiene un repositorio por nombre.

        Args:
            source_name: Nombre del repositorio (ej: 'windy_gfs', 'wrf_smn')

        Returns:
            Instancia del repositorio o None si no existe
        """
        # Mapeo de nombres de fuente a nombres de repositorio
        # Solo Windy y AWS WRF-SMN están disponibles
        source_map = {
            "windy_ecmwf": "Windy-ECMWF",
            "windy_gfs": "Windy-GFS",
            "windy_icon": "Windy-ICON",
            "wrf_smn": "WRF-SMN",
        }

        repo_name = source_map.get(source_name.lower())
        if repo_name and repo_name in self.repositories:
            return self.repositories[repo_name]

        return None

    def get_all_repositories(self) -> Dict[str, IWeatherRepository]:
        """Retorna todos los repositorios disponibles."""
        return self.repositories.copy()


def create_repository(repository_type: str, **kwargs) -> Optional[IWeatherRepository]:
    """
    Crear un repositorio según el tipo especificado.

    Args:
        repository_type: Tipo de repositorio ('windy', 'aws_smn', 'wrfsmn')
        **kwargs: Argumentos adicionales para el repositorio

    Returns:
        Instancia del repositorio o None si hay error

    Raises:
        ValueError: Si el tipo de repositorio no es válido
    """
    if repository_type == "windy":
        # Windy Point Forecast API usa WINDY_POINT_FORECAST_API_KEY
        api_key = kwargs.get("api_key") or os.getenv("WINDY_POINT_FORECAST_API_KEY")
        default_model = kwargs.get("default_model", "gfs")
        if not api_key:
            logger.error("WINDY_POINT_FORECAST_API_KEY no configurado")
            raise ValueError("WINDY_POINT_FORECAST_API_KEY no configurado")
        return WindyRepository(api_key=api_key, default_model=default_model)

    elif repository_type == "aws_smn" or repository_type == "wrfsmn":
        if not WRFSMN_AVAILABLE:
            logger.warning(
                "WRFSMNRepository no disponible: boto3, s3fs o xarray no están instalados. "
                "Instala con: pip install boto3 s3fs xarray netCDF4"
            )
            raise ValueError(
                "WRFSMNRepository requiere boto3, s3fs y xarray. "
                "Instala con: pip install boto3 s3fs xarray netCDF4"
            )
        # WRF-SMN solo usa AWS S3, sin fallback a otros servicios
        cache_ttl_hours = kwargs.get("cache_ttl_hours", 6)
        return WRFSMNRepository(
            use_meteosource_fallback=False,  # Siempre False - solo AWS S3
            cache_ttl_hours=cache_ttl_hours,
        )

    else:
        raise ValueError(f"Tipo de repositorio no válido: {repository_type}")


def _is_wrf_smn_enabled() -> bool:
    """Feature toggle: WRF-SMN habilitado solo si WRF_SMN_ENABLED=true."""
    return os.getenv("WRF_SMN_ENABLED", "false").strip().lower() == "true"


def _get_wrf_cache_ttl_hours() -> int:
    """TTL del cache WRF-SMN en horas (default 6). Variable WRF_SMN_CACHE_TTL_HOURS."""
    raw = os.getenv("WRF_SMN_CACHE_TTL_HOURS", "6").strip()
    try:
        val = int(raw)
        return max(1, min(24, val))  # Clamp 1–24 h
    except ValueError:
        return 6


def create_all_available_repositories() -> Dict[str, IWeatherRepository]:
    """
    Crear todos los repositorios disponibles según configuración.

    WRF-SMN se crea solo si WRF_SMN_ENABLED=true (default: false).
    """
    repositories: Dict[str, IWeatherRepository] = {}

    # Windy
    try:
        if os.getenv("WINDY_POINT_FORECAST_API_KEY"):
            windy_gfs = create_repository("windy", default_model="gfs")
            repositories["Windy-GFS"] = windy_gfs
            logger.info("Repositorio Windy-GFS creado")
    except Exception as e:
        logger.warning("No se pudo crear repositorio Windy: %s", e)

    # WRF-SMN: habilitado por feature toggle WRF_SMN_ENABLED (default false)
    if _is_wrf_smn_enabled() and WRFSMN_AVAILABLE:
        try:
            cache_ttl_hours = _get_wrf_cache_ttl_hours()
            wrf_smn = WRFSMNRepository(
                use_meteosource_fallback=False,
                cache_ttl_hours=cache_ttl_hours,
            )
            repositories["WRF-SMN"] = wrf_smn
            logger.info("Repositorio WRF-SMN creado (WRF_SMN_ENABLED=true)")
        except Exception as e:
            logger.warning("No se pudo crear repositorio WRF-SMN: %s", e)

    logger.info("Repositorios creados: %s", list(repositories.keys()))
    return repositories
