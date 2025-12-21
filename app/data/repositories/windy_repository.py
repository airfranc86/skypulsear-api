"""Repositorio para datos de Windy API (ECMWF, GFS, ICON)."""

import os
import time
import math
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

from app.data.repositories.base_repository import IWeatherRepository
from app.models.weather_data import WeatherData
from app.utils.exceptions import WeatherAPIError
from app.utils.logging_config import get_logger
from app.utils.constants import HTTP_TIMEOUT

logger = get_logger(__name__)


class WindyRepository(IWeatherRepository):
    """
    Repositorio para obtener datos de Windy API.

    Soporta múltiples modelos meteorológicos:
    - ECMWF (European Centre for Medium-Range Weather Forecasts)
    - GFS (Global Forecast System)
    - ICON (ICOsahedral Nonhydrostatic)
    """

    # Modelos disponibles en Windy API según documentación oficial
    # Para Argentina/Córdoba: usar GFS o cams (modelos globales)
    AVAILABLE_MODELS = ["gfs", "cams", "iconEu", "arome", "namConus", "namHawaii", "namAlaska", "gfsWave"]
    
    # Modelos globales recomendados para Argentina
    GLOBAL_MODELS = ["gfs", "cams"]

    def __init__(self, api_key: Optional[str] = None, default_model: str = "gfs"):
        """
        Inicializar repositorio Windy.

        Args:
            api_key: API key de Windy. Si es None, busca en variables de entorno.
            default_model: Modelo por defecto ('gfs', 'cams', etc.)
                          GFS recomendado para Argentina (modelo global, actualizaciones frecuentes)
        """
        self.api_key = api_key or os.getenv("WINDY_API_KEY")
        if not self.api_key:
            raise ValueError("WINDY_API_KEY no configurado")

        if default_model not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Modelo no válido: {default_model}. Opciones: {self.AVAILABLE_MODELS}"
            )

        self.default_model = default_model
        self.base_url = "https://api.windy.com/api/point-forecast/v2"
        self.timeout = HTTP_TIMEOUT
        
        # Parámetros meteorológicos a solicitar
        self.parameters = ["temp", "dewpoint", "precip", "wind", "windGust", "pressure", "rh", "lclouds", "mclouds", "hclouds"]
        self.levels = ["surface"]  # Nivel de superficie por defecto
        
        logger.info(f"WindyRepository inicializado con modelo: {default_model.upper()}")

    def get_current_weather(
        self, latitude: float, longitude: float, model: Optional[str] = None
    ) -> Optional[WeatherData]:
        """
        Obtener condiciones meteorológicas actuales desde Windy.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            model: Modelo a usar ('ecmwf', 'gfs', 'icon'). Si None, usa default_model

        Returns:
            WeatherData con condiciones actuales o None si hay error
        """
        model = model or self.default_model
        
        # Retry con backoff exponencial para errores DNS/red
        max_retries = 3
        retry_delay = 1  # segundos
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}"
                # Windy API requiere POST con JSON body según documentación
                payload = {
                    "lat": latitude,
                    "lon": longitude,
                    "model": model,
                    "parameters": self.parameters,
                    "levels": self.levels,
                    "key": self.api_key,
                }

                logger.info(
                    f"Obteniendo datos actuales de Windy ({model.upper()}) para ({latitude}, {longitude}) - Intento {attempt + 1}/{max_retries}"
                )
                response = requests.post(url, json=payload, timeout=self.timeout, headers={"Content-Type": "application/json"})
                
                logger.info(f"Windy response status: {response.status_code}")
                response.raise_for_status()

                data = response.json()
                result = self._extract_current_weather(data, latitude, longitude, model)
                if result:
                    logger.info(f"Datos actuales extraídos exitosamente de Windy ({model.upper()})")
                else:
                    logger.warning(f"No se pudieron extraer datos actuales de Windy ({model.upper()})")
                return result

            except ConnectionError as e:
                # Error DNS o conexión - retry con backoff
                error_msg = str(e)
                if "Failed to resolve" in error_msg or "Name or service not known" in error_msg:
                    logger.warning(
                        f"Error DNS al conectar con Windy (intento {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))  # Backoff exponencial
                        continue
                    else:
                        logger.error(f"Error DNS persistente después de {max_retries} intentos: {e}")
                        return None
                else:
                    logger.error(f"Error de conexión con Windy: {e}")
                    return None
                    
            except Timeout as e:
                logger.error(f"Timeout obteniendo datos actuales de Windy: {e}")
                return None  # No retry para timeouts
                
            except RequestException as e:
                # Otros errores HTTP (401, 403, 500, etc.) - no retry
                logger.error(f"Error HTTP obteniendo datos actuales de Windy: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Status code: {e.response.status_code}, Response: {e.response.text[:200]}")
                return None
                
            except Exception as e:
                logger.error(f"Error inesperado obteniendo datos actuales: {e}")
                return None
        
        return None

    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        hours: int = 72,
        model: Optional[str] = None,
    ) -> List[WeatherData]:
        """
        Obtener pronóstico meteorológico desde Windy.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            hours: Número de horas de pronóstico (default: 72, máximo según modelo)
            model: Modelo a usar ('ecmwf', 'gfs', 'icon'). Si None, usa default_model

        Returns:
            Lista de WeatherData con pronóstico
        """
        model = model or self.default_model
        
        # Retry con backoff exponencial para errores DNS/red
        max_retries = 3
        retry_delay = 1  # segundos
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}"
                # Windy API requiere POST con JSON body según documentación
                payload = {
                    "lat": latitude,
                    "lon": longitude,
                    "model": model,
                    "parameters": self.parameters,
                    "levels": self.levels,
                    "key": self.api_key,
                }

                logger.info(
                    f"Obteniendo pronóstico de Windy ({model.upper()}) para ({latitude}, {longitude}), {hours}h - Intento {attempt + 1}/{max_retries}"
                )
                response = requests.post(url, json=payload, timeout=self.timeout, headers={"Content-Type": "application/json"})
                
                logger.info(f"Windy forecast response status: {response.status_code}")
                response.raise_for_status()

                data = response.json()
                forecast = self._extract_forecast(data, latitude, longitude, hours, model)

                logger.info(f"Pronóstico obtenido: {len(forecast)} puntos de Windy ({model.upper()})")
                return forecast

            except ConnectionError as e:
                # Error DNS o conexión - retry con backoff
                error_msg = str(e)
                if "Failed to resolve" in error_msg or "Name or service not known" in error_msg:
                    logger.warning(
                        f"Error DNS al conectar con Windy (intento {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (2 ** attempt))  # Backoff exponencial
                        continue
                    else:
                        logger.error(f"Error DNS persistente después de {max_retries} intentos: {e}")
                        return []
                else:
                    logger.error(f"Error de conexión con Windy: {e}")
                    return []
                    
            except Timeout as e:
                logger.error(f"Timeout obteniendo pronóstico de Windy: {e}")
                return []  # No retry para timeouts
                
            except RequestException as e:
                # Otros errores HTTP (401, 403, 500, etc.) - no retry
                logger.error(f"Error HTTP obteniendo pronóstico de Windy: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Status code: {e.response.status_code}, Response: {e.response.text[:200]}")
                return []
                
            except Exception as e:
                logger.error(f"Error inesperado obteniendo pronóstico: {e}")
                return []
        
        return []

    def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> List[WeatherData]:
        """
        Obtener datos históricos desde Windy.

        Nota: Windy API puede tener limitaciones en datos históricos según plan.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Lista de WeatherData históricos
        """
        historical_data = []

        # Windy API puede requerir parámetros específicos para histórico
        # Ajustar según documentación oficial
        try:
            url = f"{self.base_url}"
            params = {
                "lat": latitude,
                "lon": longitude,
                "model": self.default_model,
                "key": self.api_key,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            }

            logger.debug(
                f"Obteniendo histórico de Windy para ({latitude}, {longitude})"
            )
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            # Procesar datos históricos según estructura de respuesta
            # (ajustar según documentación de Windy)

        except requests.exceptions.RequestException as e:
            logger.warning(f"Histórico no disponible de Windy: {e}")

        return historical_data

    def get_forecast_multiple_models(
        self,
        latitude: float,
        longitude: float,
        hours: int = 72,
        models: Optional[List[str]] = None,
    ) -> Dict[str, List[WeatherData]]:
        """
        Obtener pronóstico de múltiples modelos simultáneamente.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            hours: Número de horas de pronóstico
            models: Lista de modelos a consultar. Si None, usa todos los disponibles

        Returns:
            Diccionario con modelo como key y lista de WeatherData como value
        """
        models = models or self.AVAILABLE_MODELS
        results = {}

        for model in models:
            if model not in self.AVAILABLE_MODELS:
                logger.warning(f"Modelo {model} no disponible, saltando")
                continue

            try:
                forecast = self.get_forecast(latitude, longitude, hours, model)
                results[model] = forecast
            except Exception as e:
                logger.error(f"Error obteniendo pronóstico de {model}: {e}")
                results[model] = []

        return results

    def _extract_current_weather(
        self, data: Dict[str, Any], latitude: float, longitude: float, model: str
    ) -> Optional[WeatherData]:
        """
        Extraer datos actuales de la respuesta de Windy.
        
        Formato de respuesta según documentación:
        - ts: array de timestamps (milliseconds desde epoch)
        - temp-surface: array de temperaturas
        - wind_u-surface, wind_v-surface: componentes del viento
        - past3hprecip-surface: precipitación acumulada 3h
        - pressure-surface: presión
        - rh-surface: humedad relativa
        - lclouds-surface, mclouds-surface, hclouds-surface: cobertura de nubes
        """
        try:
            # Obtener timestamps (milliseconds desde epoch)
            ts_array = data.get("ts", [])
            if not ts_array or len(ts_array) == 0:
                logger.warning("No se encontraron timestamps en respuesta de Windy")
                return None

            # Usar el primer timestamp para datos actuales
            timestamp_ms = ts_array[0]
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)

            # Extraer arrays de datos (índice 0 = datos actuales)
            temp_array = data.get("temp-surface", [])
            wind_u_array = data.get("wind_u-surface", [])
            wind_v_array = data.get("wind_v-surface", [])
            precip_array = data.get("past3hprecip-surface", [])
            pressure_array = data.get("pressure-surface", [])
            rh_array = data.get("rh-surface", [])
            lclouds_array = data.get("lclouds-surface", [])
            mclouds_array = data.get("mclouds-surface", [])
            hclouds_array = data.get("hclouds-surface", [])

            # Extraer valores del índice 0
            temperature = temp_array[0] if temp_array and len(temp_array) > 0 else None
            
            # Calcular velocidad y dirección del viento desde componentes u y v
            wind_speed = None
            wind_direction = None
            if wind_u_array and wind_v_array and len(wind_u_array) > 0 and len(wind_v_array) > 0:
                u = wind_u_array[0]
                v = wind_v_array[0]
                if u is not None and v is not None:
                    wind_speed = (u**2 + v**2)**0.5  # Magnitud del vector
                    # Dirección en grados (0 = Norte, 90 = Este, 180 = Sur, 270 = Oeste)
                    # atan2(u, v) da el ángulo en radianes desde el norte
                    wind_direction = (math.degrees(math.atan2(u, v)) + 360) % 360
            
            precipitation = precip_array[0] if precip_array and len(precip_array) > 0 else None
            
            # Calcular cobertura total de nubes (suma de baja, media y alta)
            cloud_cover = None
            if (lclouds_array and mclouds_array and hclouds_array and 
                len(lclouds_array) > 0 and len(mclouds_array) > 0 and len(hclouds_array) > 0):
                lc = lclouds_array[0] or 0
                mc = mclouds_array[0] or 0
                hc = hclouds_array[0] or 0
                cloud_cover = min(100, lc + mc + hc)  # Máximo 100%

            return WeatherData(
                timestamp=timestamp,
                temperature=temperature,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                precipitation=precipitation,
                cloud_cover=cloud_cover,
                source=f"Windy-{model.upper()}",
                latitude=latitude,
                longitude=longitude,
            )
        except Exception as e:
            logger.error(f"Error extrayendo datos actuales de Windy: {e}", exc_info=True)
            return None

    def _extract_forecast(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        hours: int,
        model: str,
    ) -> List[WeatherData]:
        """
        Extraer pronóstico de la respuesta de Windy.
        
        Formato: arrays paralelos donde cada índice corresponde a un timestamp.
        """
        forecast = []

        try:
            # Obtener timestamps
            ts_array = data.get("ts", [])
            if not ts_array or len(ts_array) == 0:
                logger.warning("No se encontraron timestamps en respuesta de Windy")
                return forecast

            # Limitar a las horas solicitadas
            num_points = min(len(ts_array), hours)
            
            # Extraer arrays de datos
            temp_array = data.get("temp-surface", [])
            wind_u_array = data.get("wind_u-surface", [])
            wind_v_array = data.get("wind_v-surface", [])
            precip_array = data.get("past3hprecip-surface", [])
            lclouds_array = data.get("lclouds-surface", [])
            mclouds_array = data.get("mclouds-surface", [])
            hclouds_array = data.get("hclouds-surface", [])

            # Iterar sobre cada punto temporal
            for i in range(num_points):
                timestamp_ms = ts_array[i]
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0)

                # Extraer valores del índice i
                temperature = temp_array[i] if temp_array and i < len(temp_array) else None
                
                # Calcular velocidad y dirección del viento
                wind_speed = None
                wind_direction = None
                if (wind_u_array and wind_v_array and 
                    i < len(wind_u_array) and i < len(wind_v_array)):
                    u = wind_u_array[i]
                    v = wind_v_array[i]
                    if u is not None and v is not None:
                        wind_speed = (u**2 + v**2)**0.5
                        # Dirección en grados (0 = Norte, 90 = Este, 180 = Sur, 270 = Oeste)
                        wind_direction = (math.degrees(math.atan2(u, v)) + 360) % 360
                
                precipitation = precip_array[i] if precip_array and i < len(precip_array) else None
                
                # Cobertura total de nubes
                cloud_cover = None
                if (lclouds_array and mclouds_array and hclouds_array and
                    i < len(lclouds_array) and i < len(mclouds_array) and i < len(hclouds_array)):
                    lc = lclouds_array[i] or 0
                    mc = mclouds_array[i] or 0
                    hc = hclouds_array[i] or 0
                    cloud_cover = min(100, lc + mc + hc)

                weather_data = WeatherData(
                    timestamp=timestamp,
                    temperature=temperature,
                    wind_speed=wind_speed,
                    wind_direction=wind_direction,
                    precipitation=precipitation,
                    cloud_cover=cloud_cover,
                    source=f"Windy-{model.upper()}",
                    latitude=latitude,
                    longitude=longitude,
                )
                forecast.append(weather_data)

        except Exception as e:
            logger.error(f"Error extrayendo pronóstico de Windy: {e}", exc_info=True)

        return forecast

