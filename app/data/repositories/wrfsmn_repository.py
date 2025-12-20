"""Repositorio para datos WRF-SMN desde AWS S3 o Meteosource API.

Nota: Meteosource puede proporcionar datos WRF a través de su API.
Este repositorio implementa acceso directo a AWS S3 como alternativa.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.data.repositories.base_repository import IWeatherRepository
from app.models.weather_data import WeatherData
from app.utils.exceptions import AWSConnectionError, WeatherAPIError
from app.utils.logging_config import get_logger
from app.utils.constants import HTTP_TIMEOUT

logger = get_logger(__name__)


class WRFSMNRepository(IWeatherRepository):
    """
    Repositorio para obtener datos WRF-SMN.

    Estrategia:
    1. Intentar acceso directo a AWS S3 (Open Data)
    2. Si no está disponible, usar Meteosource API (si tiene WRF disponible)
    3. Cache local con TTL 6 horas
    """

    # AWS S3 bucket para WRF-SMN Open Data
    AWS_BUCKET = "noaa-wrf-smn"
    AWS_REGION = "us-east-1"

    # Estructura de archivos en S3
    # Formato: s3://noaa-wrf-smn/wrf-smn/{YYYY}/{MM}/{DD}/{HH}/wrf-smn-{timestamp}.nc
    S3_PREFIX = "wrf-smn"

    def __init__(self, use_meteosource_fallback: bool = True, cache_ttl_hours: int = 6):
        """
        Inicializar repositorio WRF-SMN.

        Args:
            use_meteosource_fallback: Si True, usar Meteosource como fallback
            cache_ttl_hours: TTL del cache local en horas (default: 6)
        """
        self.use_meteosource_fallback = use_meteosource_fallback
        self.cache_ttl_hours = cache_ttl_hours

        # Intentar configurar cliente S3
        self.s3_client = None
        try:
            # AWS credentials opcionales (Open Data puede no requerirlas)
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

            if aws_access_key and aws_secret_key:
                self.s3_client = boto3.client(
                    "s3",
                    region_name=self.AWS_REGION,
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                )
            else:
                # Intentar sin credenciales (Open Data puede funcionar)
                self.s3_client = boto3.client("s3", region_name=self.AWS_REGION)
                logger.info("Cliente S3 configurado sin credenciales (Open Data)")
        except Exception as e:
            logger.warning(f"No se pudo configurar cliente S3: {e}")
            self.s3_client = None

        # Cliente Meteosource como fallback
        self.meteosource_repo = None
        if self.use_meteosource_fallback:
            try:
                from app.data.repositories.meteosource_repository import (
                    MeteosourceRepository,
                )

                meteosource_key = os.getenv("METEOSOURCE_API_KEY")
                if meteosource_key:
                    self.meteosource_repo = MeteosourceRepository(
                        api_key=meteosource_key
                    )
                    logger.info("Meteosource configurado como fallback para WRF-SMN")
            except Exception as e:
                logger.warning(f"No se pudo configurar Meteosource fallback: {e}")

        # Cache local (simple, en memoria)
        self._cache: Dict[str, tuple] = {}  # key: (data, timestamp)

    def get_current_weather(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherData]:
        """
        Obtener condiciones meteorológicas actuales desde WRF-SMN.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto

        Returns:
            WeatherData con condiciones actuales o None si hay error
        """
        # WRF-SMN se actualiza 4 veces al día (00, 06, 12, 18 UTC)
        # Obtener la inicialización más reciente
        now = datetime.now(UTC)
        init_hour = (now.hour // 6) * 6  # Redondear a 00, 06, 12, 18

        try:
            # Intentar desde S3
            weather_data = self._get_from_s3(latitude, longitude, now, init_hour)
            if weather_data:
                return weather_data

            # Fallback a Meteosource si está disponible
            if self.meteosource_repo:
                logger.info("Usando Meteosource como fallback para WRF-SMN")
                return self.meteosource_repo.get_current_weather(latitude, longitude)

            logger.warning("No se pudo obtener datos WRF-SMN desde ninguna fuente")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo datos actuales de WRF-SMN: {e}")
            return None

    def get_forecast(
        self, latitude: float, longitude: float, hours: int = 72
    ) -> List[WeatherData]:
        """
        Obtener pronóstico meteorológico desde WRF-SMN.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            hours: Número de horas de pronóstico (máximo 72 para WRF-SMN)

        Returns:
            Lista de WeatherData con pronóstico
        """
        if hours > 72:
            logger.warning(f"WRF-SMN solo soporta hasta 72 horas, limitando a 72")
            hours = 72

        # Obtener inicialización más reciente
        now = datetime.now(UTC)
        init_hour = (now.hour // 6) * 6
        init_time = now.replace(hour=init_hour, minute=0, second=0, microsecond=0)

        forecast = []

        try:
            # Intentar desde S3
            for hour_offset in range(hours):
                forecast_time = init_time + timedelta(hours=hour_offset)
                weather_data = self._get_from_s3(
                    latitude, longitude, forecast_time, init_hour
                )
                if weather_data:
                    forecast.append(weather_data)

            if forecast:
                logger.info(f"Pronóstico WRF-SMN obtenido: {len(forecast)} puntos")
                return forecast

            # Fallback a Meteosource
            if self.meteosource_repo:
                logger.info("Usando Meteosource como fallback para pronóstico WRF-SMN")
                return self.meteosource_repo.get_forecast(latitude, longitude, hours)

            logger.warning("No se pudo obtener pronóstico WRF-SMN desde ninguna fuente")
            return []

        except Exception as e:
            logger.error(f"Error obteniendo pronóstico de WRF-SMN: {e}")
            return []

    def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> List[WeatherData]:
        """
        Obtener datos históricos desde WRF-SMN.

        Nota: Disponible desde abril 2022.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Lista de WeatherData históricos
        """
        historical_data = []
        current_date = start_date

        while current_date <= end_date:
            try:
                # WRF-SMN tiene datos cada 6 horas (00, 06, 12, 18 UTC)
                for hour in [0, 6, 12, 18]:
                    forecast_time = current_date.replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                    if forecast_time > end_date:
                        break

                    init_hour = hour
                    weather_data = self._get_from_s3(
                        latitude, longitude, forecast_time, init_hour
                    )
                    if weather_data:
                        historical_data.append(weather_data)

            except Exception as e:
                logger.warning(
                    f"Error obteniendo histórico WRF-SMN para {current_date}: {e}"
                )

            current_date += timedelta(days=1)

        return historical_data

    def _get_from_s3(
        self, latitude: float, longitude: float, forecast_time: datetime, init_hour: int
    ) -> Optional[WeatherData]:
        """
        Obtener datos desde AWS S3.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            forecast_time: Tiempo del pronóstico
            init_hour: Hora de inicialización (0, 6, 12, 18)

        Returns:
            WeatherData o None si hay error
        """
        if not self.s3_client:
            return None

        # Construir clave S3
        init_date = forecast_time.replace(
            hour=init_hour, minute=0, second=0, microsecond=0
        )
        date_str = init_date.strftime("%Y/%m/%d/%H")
        s3_key = f"{self.S3_PREFIX}/{date_str}/wrf-smn-{init_date.isoformat()}.nc"

        # Verificar cache
        cache_key = f"{s3_key}_{latitude}_{longitude}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (
                datetime.now() - cached_time
            ).total_seconds() < self.cache_ttl_hours * 3600:
                return cached_data

        try:
            # Descargar archivo NetCDF desde S3
            # Nota: Esto requiere netCDF4 y xarray (agregar a requirements.txt)
            # Por ahora, retornar None y usar fallback

            # TODO: Implementar lectura de NetCDF
            # import xarray as xr
            # with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as tmp_file:
            #     self.s3_client.download_fileobj(self.AWS_BUCKET, s3_key, tmp_file)
            #     ds = xr.open_dataset(tmp_file.name)
            #     # Extraer datos para lat/lon específicos
            #     # Convertir a WeatherData

            logger.debug(f"Lectura de NetCDF desde S3 no implementada aún: {s3_key}")
            return None

        except ClientError as e:
            logger.warning(f"Error accediendo a S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Error procesando datos WRF-SMN desde S3: {e}")
            return None

    def _extract_weather_from_netcdf(
        self,
        ds: Any,  # xarray.Dataset
        latitude: float,
        longitude: float,
        forecast_time: datetime,
    ) -> Optional[WeatherData]:
        """
        Extraer datos meteorológicos desde dataset NetCDF.

        Args:
            ds: Dataset xarray con datos WRF-SMN
            latitude: Latitud del punto
            longitude: Longitud del punto
            forecast_time: Tiempo del pronóstico

        Returns:
            WeatherData o None si hay error
        """
        try:
            # TODO: Implementar extracción de variables desde NetCDF
            # Variables esperadas:
            # - T2: Temperatura a 2m
            # - RH2: Humedad relativa a 2m
            # - U10, V10: Componentes de viento a 10m
            # - RAINC, RAINNC: Precipitación acumulada

            # Ejemplo de código (requiere xarray):
            # temp = ds.sel(lat=latitude, lon=longitude, method='nearest')['T2'].values
            # wind_u = ds.sel(lat=latitude, lon=longitude, method='nearest')['U10'].values
            # wind_v = ds.sel(lat=latitude, lon=longitude, method='nearest')['V10'].values
            # wind_speed = np.sqrt(wind_u**2 + wind_v**2)
            # wind_direction = np.arctan2(wind_v, wind_u) * 180 / np.pi

            return None

        except Exception as e:
            logger.error(f"Error extrayendo datos desde NetCDF: {e}")
            return None
