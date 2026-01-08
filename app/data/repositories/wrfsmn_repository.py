"""Repositorio para datos WRF-SMN desde AWS S3 o Meteosource API.

Nota: Meteosource puede proporcionar datos WRF a través de su API.
Este repositorio implementa acceso directo a AWS S3 como alternativa.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import UTC, datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
import s3fs
import xarray as xr
import numpy as np

from app.utils.s3_utils import s3_bucket_manager

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

        # Configurar acceso a S3 WRF-SMN Open Data (sin credenciales)
        self.s3_fs = None
        try:
            # Para WRF-SMN Open Data, usamos acceso anónimo forzado
            logger.info("Configurando acceso anónimo a WRF-SMN Open Data...")

            # Limpiar temporalmente variables AWS para forzar acceso anónimo
            aws_vars = [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AWS_PROFILE",
            ]
            old_values = {}
            for var in aws_vars:
                old_values[var] = os.environ.pop(var, None)

            try:
                # Configurar s3fs anónimo (probado y funciona)
                self.s3_fs = s3fs.S3FileSystem(anon=True)

                # Probar acceso al bucket
                test_path = f"s3://{self.AWS_BUCKET}"
                if self.s3_fs.exists(test_path):
                    logger.info(
                        f"✅ Acceso anónimo exitoso a WRF-SMN: {self.AWS_BUCKET}"
                    )
                else:
                    logger.error(f"No se puede acceder al bucket {self.AWS_BUCKET}")
                    self.s3_fs = None

            finally:
                # Restaurar variables de entorno
                for var, value in old_values.items():
                    if value is not None:
                        os.environ[var] = value

        except Exception as e:
            logger.error(f"No se pudo configurar acceso S3 anónimo: {e}")
            self.s3_fs = None

        except Exception as e:
            logger.error(f"No se pudo configurar S3 con Bucket Keys: {e}")
            self.s3_fs = None
        try:
            # Intentar usar credenciales si están disponibles
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")

            # Configuración con Bucket Keys support
            s3_config = Config(
                region_name=aws_region,
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "adaptive"},
            )

            if aws_access_key and aws_secret_key:
                # Usar credenciales explícitas (si se proporcionan)
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    config=s3_config,
                )
                self.s3_fs = s3fs.S3FileSystem(
                    key=aws_access_key,
                    secret=aws_secret_key,
                    client_kwargs={"region_name": aws_region},
                )
                logger.info("S3FileSystem configurado con credenciales AWS")
            else:
                # Acceso anónimo para Open Data (fallback)
                self.s3_fs = s3fs.S3FileSystem(anon=True)
                logger.info("S3FileSystem configurado para acceso anónimo (Open Data)")

            logger.info(f"Bucket S3 configurado: {self.AWS_BUCKET}")

        except Exception as e:
            logger.error(f"No se pudo configurar S3: {e}")
            self.s3_fs = None
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

            # Abrir dataset directamente desde S3 con Bucket Keys support
            # El bucket de Open Data usa acceso público, pero configuramos headers para Bucket Keys
            try:
                # Configurar headers para S3 Bucket Keys si se usa cliente con credenciales
                s3_kwargs = {"mode": "rb"}
                if self.s3_client:
                    # Agregar headers para Bucket Keys según documentación AWS
                    bucket_key_enabled = (
                        os.getenv("AWS_S3_BUCKET_KEY_ENABLED", "true").lower() == "true"
                    )
                    if bucket_key_enabled:
                        s3_kwargs["additional_headers"] = {
                            "x-amz-server-side-encryption-bucket-key-enabled": "true"
                        }
                        logger.debug("S3 Bucket Keys habilitados para este request")

                with self.s3_fs.open(s3_path, **s3_kwargs) as f:
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
    self, ds: xr.Dataset, latitude: float, longitude: float, forecast_time: datetime
) -> Optional[WeatherData]:
    """
    Extraer datos meteorológicos para coordenadas específicas desde NetCDF de WRF-SMN.

    Args:
        ds: Dataset xarray del NetCDF
        latitude: Latitud del punto
        longitude: Longitud del punto
        forecast_time: Tiempo del pronóstico

    Returns:
        WeatherData con datos extraídos o None si hay error
    """
    try:
        # Extraer coordenadas del grid WRF (siempre 2D en WRF-SMN)
        if "lat" in ds.coords and "lon" in ds.coords:
            lats = ds.coords["lat"].values  # 2D array (y, x)
            lons = ds.coords["lon"].values  # 2D array (y, x)

            logger.debug(f"Shape coordenadas WRF: {lats.shape}")
            logger.debug(f"Rango lat: {lats.min():.2f} a {lats.max():.2f}")
            logger.debug(f"Rango lon: {lons.min():.2f} a {lons.max():.2f}")

            # Encontrar punto más cercano en grid 2D
            lat_diff = lats - latitude
            lon_diff = lons - longitude
            distance = np.sqrt(lat_diff**2 + lon_diff**2)

            lat_idx, lon_idx = np.unravel_index(np.argmin(distance), distance.shape)
            lat_closest = lats[lat_idx, lon_idx]
            lon_closest = lons[lat_idx, lon_idx]
            dist_min = distance[lat_idx, lon_idx]

            logger.debug(f"Punto más cercano: ({lat_closest:.4f}, {lon_closest:.4f})")
            logger.debug(f"Índices: ({lat_idx}, {lon_idx}), distancia: {dist_min:.4f}°")
        else:
            logger.error(
                "Coordenadas 'lat' y 'lon' no encontradas en el NetCDF WRF-SMN"
            )
            return None

        # Extraer variables meteorológicas WRF-SMN
        weather_data = {}

        # Temperatura (WRF usa T2 para temperatura a 2m)
        if "T2" in ds.data_vars:
            try:
                temp_array = ds.data_vars["T2"]
                if "time" in temp_array.dims:
                    temp = temp_array.isel(time=0, y=lat_idx, x=lon_idx).values
                else:
                    temp = temp_array.isel(y=lat_idx, x=lon_idx).values

                # WRF-SMN T2 está en Kelvin, convertir a Celsius
                if temp > 100:  # Verificar si está en Kelvin
                    temp = temp - 273.15

                # Validación básica (rango razonable para Argentina)
                if -50 <= temp <= 60:
                    weather_data["temperature"] = float(temp)
                else:
                    logger.warning(f"Temperatura WRF-SMN fuera de rango: {temp}°C")

            except Exception as e:
                logger.warning(f"No se pudo extraer T2: {e}")

        # Precipitación (WRF-SMN usa PP para precipitación acumulada)
        if "PP" in ds.data_vars:
            try:
                precip_array = ds.data_vars["PP"]
                if "time" in precip_array.dims:
                    precip = precip_array.isel(time=0, y=lat_idx, x=lon_idx).values
                else:
                    precip = precip_array.isel(y=lat_idx, x=lon_idx).values

                # PP está en mm, validar rango razonable
                if 0 <= precip <= 500:
                    weather_data["precipitation"] = float(precip)
                else:
                    logger.warning(f"Precipitación WRF-SMN fuera de rango: {precip}mm")

            except Exception as e:
                logger.warning(f"No se pudo extraer PP: {e}")

        # Viento (WRF-SMN usa magViento10 y dirViento10)
        if "magViento10" in ds.data_vars:
            try:
                wind_array = ds.data_vars["magViento10"]
                if "time" in wind_array.dims:
                    wind = wind_array.isel(time=0, y=lat_idx, x=lon_idx).values
                else:
                    wind = wind_array.isel(y=lat_idx, x=lon_idx).values

                # Validar rango de velocidad de viento (0-100 m/s)
                if 0 <= wind <= 100:
                    weather_data["wind_speed"] = float(wind)
                else:
                    logger.warning(f"Viento WRF-SMN fuera de rango: {wind}m/s")

            except Exception as e:
                logger.warning(f"No se pudo extraer magViento10: {e}")

        # Dirección del viento
        if "dirViento10" in ds.data_vars:
            try:
                dir_array = ds.data_vars["dirViento10"]
                if "time" in dir_array.dims:
                    wind_dir = dir_array.isel(time=0, y=lat_idx, x=lon_idx).values
                else:
                    wind_dir = dir_array.isel(y=lat_idx, x=lon_idx).values

                # Normalizar dirección (0-360°)
                if 0 <= wind_dir <= 360:
                    weather_data["wind_direction"] = float(wind_dir)
                else:
                    weather_data["wind_direction"] = float(wind_dir % 360)

            except Exception as e:
                logger.warning(f"No se pudo extraer dirViento10: {e}")

        # Humedad relativa (WRF-SMN usa HR2)
        if "HR2" in ds.data_vars:
            try:
                humid_array = ds.data_vars["HR2"]
                if "time" in humid_array.dims:
                    humidity = humid_array.isel(time=0, y=lat_idx, x=lon_idx).values
                else:
                    humidity = humid_array.isel(y=lat_idx, x=lon_idx).values

                # Validar rango de humedad (0-100%)
                if 0 <= humidity <= 100:
                    weather_data["humidity"] = float(humidity)
                else:
                    logger.warning(f"Humedad WRF-SMN fuera de rango: {humidity}%")

            except Exception as e:
                logger.warning(f"No se pudo extraer HR2: {e}")

        # Presión (WRF-SMN usa PSFC)
        if "PSFC" in ds.data_vars:
            try:
                press_array = ds.data_vars["PSFC"]
                if "time" in press_array.dims:
                    pressure = press_array.isel(time=0, y=lat_idx, x=lon_idx).values
                else:
                    pressure = press_array.isel(y=lat_idx, x=lon_idx).values

                # WRF-SMN PSFC está en Pa, convertir a hPa
                if pressure > 50000:  # Probablemente en Pa
                    pressure = pressure / 100

                # Validar rango de presión (800-1100 hPa)
                if 800 <= pressure <= 1100:
                    weather_data["pressure"] = float(pressure)
                else:
                    logger.warning(f"Presión WRF-SMN fuera de rango: {pressure}hPa")

            except Exception as e:
                logger.warning(f"No se pudo extraer PSFC: {e}")

        # Validar datos mínimos necesarios
        if not weather_data:
            logger.error(
                "No se extrajeron datos meteorológicos válidos del NetCDF WRF-SMN"
            )
            return None

        # Asegurar valores por defecto si faltan
        weather_data.setdefault("temperature", 20.0)
        weather_data.setdefault("humidity", 50.0)
        weather_data.setdefault("pressure", 1013.25)
        weather_data.setdefault("wind_speed", 0.0)
        weather_data.setdefault("precipitation", 0.0)

        # Crear objeto WeatherData
        weather = WeatherData(
            latitude=latitude,
            longitude=longitude,
            timestamp=forecast_time,
            temperature=weather_data["temperature"],
            humidity=weather_data["humidity"],
            pressure=weather_data["pressure"],
            wind_speed=weather_data["wind_speed"],
            wind_direction=weather_data.get("wind_direction"),
            precipitation=weather_data["precipitation"],
            source="WRF-SMN",
            model="WRF-DET",
            resolution="4km",
            coordinates_closest=(lat_closest, lon_closest),
            grid_indices=(lat_idx, lon_idx),
            grid_distance=dist_min,
        )

        logger.info(
            f"Datos WRF-SMN extraídos para ({latitude:.2f}, {longitude:.2f}): "
            f"T={weather.temperature:.1f}°C, "
            f"H={weather.humidity:.1f}%, "
            f"P={weather.precipitation:.1f}mm, "
            f"V={weather.wind_speed:.1f}m/s, "
            f"Dist={dist_min:.4f}°"
        )

        return weather

    except Exception as e:
        logger.error(f"Error extrayendo datos del NetCDF WRF-SMN: {e}")
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
