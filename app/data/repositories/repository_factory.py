"""Factory para crear repositorios de datos meteorológicos."""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

from app.data.repositories.base_repository import IWeatherRepository
from app.data.repositories.meteosource_repository import MeteosourceRepository
from app.data.repositories.local_stations_repository import LocalStationsRepository
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
            source_name: Nombre del repositorio (ej: 'meteosource', 'windy_ecmwf')

        Returns:
            Instancia del repositorio o None si no existe
        """
        # Mapeo de nombres de fuente a nombres de repositorio
        source_map = {
            "meteosource": "Meteosource",
            "meteosource_wrf": "Meteosource",
            "windy_ecmwf": "Windy-ECMWF",
            "windy_gfs": "Windy-GFS",
            "windy_icon": "Windy-ICON",
            "wrf_smn": "WRF-SMN",
            "local_stations": "Estaciones Locales",
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
        repository_type: Tipo de repositorio ('meteosource', 'local_stations', 'aws_smn')
        **kwargs: Argumentos adicionales para el repositorio

    Returns:
        Instancia del repositorio o None si hay error

    Raises:
        ValueError: Si el tipo de repositorio no es válido
    """
    if repository_type == "meteosource":
        api_key = kwargs.get("api_key") or os.getenv("METEOSOURCE_API_KEY")
        if not api_key:
            logger.error("METEOSOURCE_API_KEY no configurado")
            raise ValueError("METEOSOURCE_API_KEY no configurado")
        return MeteosourceRepository(api_key=api_key)

    elif repository_type == "local_stations":
        csv_path = kwargs.get("csv_path") or os.getenv(
            "LOCAL_STATIONS_PATH", "StationCba.csv"
        )
        return LocalStationsRepository(csv_path=csv_path)

    elif repository_type == "windy":
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
        use_meteosource_fallback = kwargs.get("use_meteosource_fallback", True)
        cache_ttl_hours = kwargs.get("cache_ttl_hours", 6)
        return WRFSMNRepository(
            use_meteosource_fallback=use_meteosource_fallback,
            cache_ttl_hours=cache_ttl_hours,
        )

    else:
        raise ValueError(f"Tipo de repositorio no válido: {repository_type}")


def create_all_available_repositories() -> Dict[str, IWeatherRepository]:
    """
    Crear todos los repositorios disponibles según configuración.

    Returns:
        Diccionario con nombre de repositorio como key e instancia como value
    """
    repositories = {}

    # Meteosource
    try:
        if os.getenv("METEOSOURCE_API_KEY"):
            repositories["Meteosource"] = create_repository("meteosource")
            logger.info("Repositorio Meteosource creado")
    except Exception as e:
        logger.warning(f"No se pudo crear repositorio Meteosource: {e}")

    # Local Stations
    try:
        csv_path = os.getenv("LOCAL_STATIONS_PATH", "StationCba.csv")
        repositories["Estaciones Locales"] = create_repository(
            "local_stations", csv_path=csv_path
        )
        logger.info("Repositorio de Estaciones Locales creado")
    except Exception as e:
        logger.warning(f"No se pudo crear repositorio de Estaciones Locales: {e}")

    # Windy
    try:
        if os.getenv("WINDY_POINT_FORECAST_API_KEY"):
            # Solo GFS disponible (modelo global, actualizaciones frecuentes)
            # CAMS removido: no retorna datos para la región
            windy_gfs = create_repository("windy", default_model="gfs")
            repositories["Windy-GFS"] = windy_gfs
            logger.info("Repositorio Windy-GFS creado")
    except Exception as e:
        logger.warning(f"No se pudo crear repositorio Windy: {e}")

    # WRF-SMN (AWS S3 o Meteosource fallback)
    if WRFSMN_AVAILABLE:
        try:
            # Intentar crear repositorio WRF-SMN
            # No requiere credenciales AWS (Open Data)
            repositories["WRF-SMN"] = create_repository(
                "wrfsmn", use_meteosource_fallback=True
            )
            logger.info("Repositorio WRF-SMN creado")
        except Exception as e:
            logger.warning(f"No se pudo crear repositorio WRF-SMN: {e}")
    else:
        logger.info(
            "WRFSMNRepository no disponible: boto3, s3fs o xarray no están instalados. "
            "Omitiendo repositorio WRF-SMN."
        )

    logger.info(f"Repositorios creados: {list(repositories.keys())}")
    return repositories
