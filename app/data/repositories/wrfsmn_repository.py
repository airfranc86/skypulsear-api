"""Repositorio para datos WRF-SMN desde AWS S3 o Meteosource API.

Nota: Meteosource puede proporcionar datos WRF a través de su API.
Este repositorio implementa acceso directo a AWS S3 como alternativa.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import UTC, datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import s3fs
import xarray as xr
import numpy as np

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
    # NOTA: El bucket correcto es "smn-ar-wrf" según documentación oficial
    # Referencia: https://registry.opendata.aws/smn-ar-wrf-dataset/
    AWS_BUCKET = "smn-ar-wrf"
    AWS_REGION = "us-west-2"  # Región correcta según documentación

    # Estructura de archivos en S3
    # Formato: s3://smn-ar-wrf/DATA/WRF/DET/{YYYY}/{MM}/{DD}/{HH}/WRFDETAR_01H_{YYYYMMDD}_{HH}_{forecast_hour}.nc
    # Ejemplo: s3://smn-ar-wrf/DATA/WRF/DET/2022/03/21/00/WRFDETAR_01H_20220321_00_002.nc
    # Donde:
    #   - {YYYY}/{MM}/{DD}/{HH} = Fecha y hora de inicialización del modelo
    #   - {forecast_hour} = Hora de pronóstico (000, 001, 002, ..., 072)
    S3_PREFIX = "DATA/WRF/DET"

    def __init__(self, use_meteosource_fallback: bool = True, cache_ttl_hours: int = 6):
        """
        Inicializar repositorio WRF-SMN.

        Args:
            use_meteosource_fallback: Si True, usar Meteosource como fallback
            cache_ttl_hours: TTL del cache local en horas (default: 6)
        """
        self.use_meteosource_fallback = use_meteosource_fallback
        self.cache_ttl_hours = cache_ttl_hours

        # Configurar acceso a S3 (Open Data - acceso anónimo)
        self.s3_fs = None
        try:
            # s3fs permite acceso anónimo a Open Data sin credenciales
            self.s3_fs = s3fs.S3FileSystem(anon=True)
            logger.info("S3FileSystem configurado para acceso anónimo (Open Data)")
        except Exception as e:
            logger.warning(f"No se pudo configurar S3FileSystem: {e}")
            self.s3_fs = None

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
        if not self.s3_fs:
            return None

        # Construir clave S3 con formato correcto de WRF-SMN
        init_date = forecast_time.replace(
            hour=init_hour, minute=0, second=0, microsecond=0
        )

        # Calcular forecast_hour (diferencia entre forecast_time e init_time)
        forecast_hour = int((forecast_time - init_date).total_seconds() / 3600)

        # Validar que forecast_hour esté en rango válido (0-72)
        if forecast_hour < 0 or forecast_hour > 72:
            logger.warning(f"Forecast hour {forecast_hour} fuera de rango (0-72)")
            return None

        # Formato: WRFDETAR_01H_{YYYYMMDD}_{HH}_{forecast_hour:03d}.nc
        # Ejemplo: WRFDETAR_01H_20220321_00_002.nc
        date_str = init_date.strftime("%Y/%m/%d/%H")
        filename = f"WRFDETAR_01H_{init_date.strftime('%Y%m%d')}_{init_hour:02d}_{forecast_hour:03d}.nc"
        s3_key = f"{self.S3_PREFIX}/{date_str}/{filename}"

        # Verificar cache
        cache_key = f"{s3_key}_{latitude}_{longitude}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (
                datetime.now() - cached_time
            ).total_seconds() < self.cache_ttl_hours * 3600:
                return cached_data

        try:
            # Verificar que s3fs esté configurado
            if not self.s3_fs:
                logger.warning("S3FileSystem no configurado, no se puede acceder a S3")
                return None

            # Construir ruta S3 completa
            s3_path = f"s3://{self.AWS_BUCKET}/{s3_key}"

            logger.debug(f"Intentando leer NetCDF desde S3: {s3_path}")

            # Abrir dataset directamente desde S3 (streaming, no descarga completa)
            # s3fs permite acceso anónimo a Open Data
            try:
                with self.s3_fs.open(s3_path, mode="rb") as f:
                    # Abrir con xarray (streaming, solo lee lo necesario)
                    ds = xr.open_dataset(f, decode_times=True)

                    # Extraer datos para coordenadas específicas
                    weather_data = self._extract_weather_from_netcdf(
                        ds, latitude, longitude, forecast_time
                    )

                    # Cerrar dataset
                    ds.close()

                    # Guardar en cache si se obtuvo datos válidos
                    if weather_data:
                        self._cache[cache_key] = (weather_data, datetime.now(UTC))
                        logger.info(f"Datos WRF-SMN obtenidos desde S3: {s3_key}")

                    return weather_data

            except FileNotFoundError:
                logger.warning(f"Archivo no encontrado en S3: {s3_path}")
                return None
            except Exception as e:
                logger.error(f"Error leyendo NetCDF desde S3: {e}")
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

        NOTA: Esta función requiere implementación completa. Ver documentación abajo.
        """
        try:
            # Verificar dimensiones y variables disponibles
            logger.debug(f"Dimensiones del dataset: {ds.dims}")
            logger.debug(f"Variables disponibles: {list(ds.data_vars)}")
            logger.debug(f"Coordenadas: {list(ds.coords)}")

            # Seleccionar punto más cercano a coordenadas solicitadas
            # WRF-SMN puede tener diferentes estructuras de coordenadas
            point = None

            # Opción 1: Si lat/lon son coordenadas 1D (más común en NetCDF estándar)
            if "lat" in ds.coords and "lon" in ds.coords:
                try:
                    point = ds.sel(lat=latitude, lon=longitude, method="nearest")
                    logger.debug(
                        f"Punto seleccionado usando coordenadas 1D: lat={latitude}, lon={longitude}"
                    )
                except Exception as e:
                    logger.warning(f"Error seleccionando punto con coordenadas 1D: {e}")

            # Opción 2: Si lat/lon son arrays 2D (grid WRF)
            if point is None and ("XLAT" in ds or "lat" in ds.data_vars):
                try:
                    # Obtener grid de coordenadas
                    if "XLAT" in ds and "XLONG" in ds:
                        lat_grid = ds["XLAT"].values
                        lon_grid = ds["XLONG"].values
                    elif "lat" in ds.data_vars and "lon" in ds.data_vars:
                        lat_grid = ds["lat"].values
                        lon_grid = ds["lon"].values
                    else:
                        raise ValueError("No se encontraron coordenadas en el dataset")

                    # Encontrar índice del punto más cercano
                    # Calcular distancia euclidiana (aproximación para distancias cortas)
                    distances = np.sqrt(
                        (lat_grid - latitude) ** 2 + (lon_grid - longitude) ** 2
                    )
                    idx = np.unravel_index(np.argmin(distances), distances.shape)

                    # Seleccionar punto usando índices
                    if "south_north" in ds.dims and "west_east" in ds.dims:
                        point = ds.isel(south_north=idx[0], west_east=idx[1])
                    else:
                        # Intentar con índices genéricos
                        point = ds.isel({ds.dims[0]: idx[0], ds.dims[1]: idx[1]})

                    logger.debug(f"Punto seleccionado usando grid 2D: índices {idx}")
                except Exception as e:
                    logger.error(f"Error seleccionando punto con grid 2D: {e}")
                    return None

            if point is None:
                logger.error("No se pudo seleccionar punto del dataset")
                return None

            # Extraer variables meteorológicas (con manejo de errores)
            temperature = None
            humidity = None
            wind_speed = None
            wind_direction = None
            pressure = None
            precipitation = None

            # Temperatura a 2m (convertir de Kelvin a Celsius)
            try:
                if "T2" in point.data_vars or "T2" in ds.data_vars:
                    temp_k = float(point["T2"].values)
                    temperature = temp_k - 273.15
                    logger.debug(f"Temperatura extraída: {temperature}°C")
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(f"Variable T2 no encontrada o no accesible: {e}")

            # Humedad relativa a 2m (%)
            try:
                if "RH2" in point.data_vars or "RH2" in ds.data_vars:
                    humidity = float(point["RH2"].values)
                    logger.debug(f"Humedad extraída: {humidity}%")
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(f"Variable RH2 no encontrada o no accesible: {e}")

            # Componentes de viento a 10m (m/s)
            try:
                if ("U10" in point.data_vars or "U10" in ds.data_vars) and (
                    "V10" in point.data_vars or "V10" in ds.data_vars
                ):
                    wind_u = float(point["U10"].values)
                    wind_v = float(point["V10"].values)

                    # Calcular velocidad y dirección del viento
                    wind_speed = float(np.sqrt(wind_u**2 + wind_v**2))
                    wind_direction = float(np.arctan2(wind_v, wind_u) * 180.0 / np.pi)

                    # Normalizar dirección (0-360)
                    if wind_direction < 0:
                        wind_direction += 360.0

                    logger.debug(
                        f"Viento extraído: {wind_speed} m/s, dirección {wind_direction}°"
                    )
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(f"Variables U10/V10 no encontradas o no accesibles: {e}")

            # Presión en superficie (convertir de Pa a hPa)
            try:
                if "PSFC" in point.data_vars or "PSFC" in ds.data_vars:
                    pressure_pa = float(point["PSFC"].values)
                    pressure = pressure_pa / 100.0
                    logger.debug(f"Presión extraída: {pressure} hPa")
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(f"Variable PSFC no encontrada o no accesible: {e}")

            # Precipitación (sumar convectiva + no convectiva)
            try:
                rainc = 0.0
                rainnc = 0.0

                if "RAINC" in point.data_vars or "RAINC" in ds.data_vars:
                    rainc = float(point["RAINC"].values)

                if "RAINNC" in point.data_vars or "RAINNC" in ds.data_vars:
                    rainnc = float(point["RAINNC"].values)

                precipitation = rainc + rainnc
                logger.debug(
                    f"Precipitación extraída: {precipitation} mm (convectiva: {rainc}, no convectiva: {rainnc})"
                )
            except (KeyError, IndexError, AttributeError) as e:
                logger.warning(
                    f"Variables RAINC/RAINNC no encontradas o no accesibles: {e}"
                )

            # Validar que al menos tengamos datos básicos
            if temperature is None and wind_speed is None and precipitation is None:
                logger.warning("No se pudieron extraer datos suficientes del dataset")
                return None

            # Crear objeto WeatherData
            weather_data = WeatherData(
                latitude=latitude,
                longitude=longitude,
                timestamp=forecast_time,
                temperature=temperature,
                humidity=humidity,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                pressure=pressure,
                precipitation=precipitation,
                source="WRF-SMN",
                model="WRF-SMN",
            )

            logger.info(
                f"Datos WRF-SMN extraídos para ({latitude}, {longitude}): "
                f"temp={temperature}°C, viento={wind_speed} m/s, precip={precipitation} mm"
            )
            return weather_data

        except Exception as e:
            logger.error(f"Error extrayendo datos desde NetCDF: {e}")
            return None
