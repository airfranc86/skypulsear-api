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
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from app.utils.circuit_breaker_registry import register_circuit_breaker
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
    AVAILABLE_MODELS = [
        "gfs",
        "cams",
        "iconEu",
        "arome",
        "namConus",
        "namHawaii",
        "namAlaska",
        "gfsWave",
    ]

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
        # Windy tiene dos APIs: Point Forecast y Map Forecast
        # Usamos WINDY_POINT_FORECAST_API_KEY para Point Forecast API
        self.api_key = api_key or os.getenv("WINDY_POINT_FORECAST_API_KEY")
        if not self.api_key:
            raise ValueError("WINDY_POINT_FORECAST_API_KEY no configurado")

        if default_model not in self.AVAILABLE_MODELS:
            raise ValueError(
                f"Modelo no válido: {default_model}. Opciones: {self.AVAILABLE_MODELS}"
            )

        self.default_model = default_model
        self.base_url = "https://api.windy.com/api/point-forecast/v2"
        self.timeout = HTTP_TIMEOUT

        # Parámetros meteorológicos a solicitar
        self.parameters = [
            "temp",
            "dewpoint",
            "precip",
            "wind",
            "windGust",
            "pressure",
            "rh",
            "lclouds",
            "mclouds",
            "hclouds",
        ]
        self.levels = ["surface"]  # Nivel de superficie por defecto

        # Circuit breaker para proteger contra cascading failures
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=(ConnectionError, Timeout, RequestException),
            name="windy_api",
        )

        # Registrar estado inicial del circuit breaker en métricas
        try:
            from app.utils.metrics import record_circuit_breaker_state

            record_circuit_breaker_state("windy_api", "closed")
        except ImportError:
            pass

        # Registrar para Risk Agent Operational Failure (lee estado sin bloquear API)
        register_circuit_breaker("windy_api", self.circuit_breaker)

        logger.info(
            "WindyRepository inicializado",
            extra={"model": default_model.upper(), "source": "windy"},
        )

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

        # Función interna con retry que será protegida por circuit breaker
        def _fetch_with_retry() -> Optional[WeatherData]:
            """Función interna con retry que será protegida por circuit breaker."""
            from app.utils.retry import retry_with_backoff

            @retry_with_backoff(
                max_attempts=3,
                initial_delay=1.0,
                multiplier=2.0,
                max_delay=10.0,
                jitter=True,
                retry_on=(ConnectionError, Timeout),
            )
            def _fetch_data():
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
                    "Obteniendo datos actuales de Windy",
                    extra={
                        "model": model.upper(),
                        "latitude": latitude,
                        "longitude": longitude,
                        "source": "windy",
                    },
                )
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )

                logger.info(
                    "Windy response recibida",
                    extra={
                        "status_code": response.status_code,
                        "model": model.upper(),
                        "source": "windy",
                    },
                )
                response.raise_for_status()

                data = response.json()
                logger.debug(
                    "Windy response procesada",
                    extra={
                        "model": model.upper(),
                        "response_keys": list(data.keys())[:15],
                        "source": "windy",
                    },
                )
                return data

            try:
                data = _fetch_data()
                result = self._extract_current_weather(data, latitude, longitude, model)
                if result:
                    logger.info(
                        "Datos actuales extraídos exitosamente",
                        extra={"model": model.upper(), "source": "windy"},
                    )
                else:
                    logger.warning(
                        "No se pudieron extraer datos actuales",
                        extra={"model": model.upper(), "source": "windy"},
                    )
                return result
            except RequestException as e:
                # Errores HTTP (401, 403, 500, etc.) - no retry
                status_code = None
                response_text = None
                if hasattr(e, "response") and e.response is not None:
                    status_code = e.response.status_code
                    response_text = e.response.text[:200] if e.response.text else None

                logger.error(
                    "Error HTTP obteniendo datos actuales de Windy",
                    extra={
                        "error": str(e),
                        "status_code": status_code,
                        "response_preview": response_text,
                        "model": model.upper(),
                        "source": "windy",
                    },
                )
                # No re-raise para errores HTTP (no son transitorios)
                return None
            except Exception as e:
                logger.error(
                    "Error inesperado obteniendo datos actuales",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "model": model.upper(),
                        "source": "windy",
                    },
                    exc_info=True,
                )
                raise  # Re-raise para que circuit breaker lo capture

        # Usar circuit breaker para proteger la llamada
        try:
            return self.circuit_breaker.call(_fetch_with_retry)
        except CircuitBreakerOpenError as e:
            logger.warning(
                "Circuit breaker abierto para Windy",
                extra={
                    "error": str(e),
                    "circuit_state": self.circuit_breaker.get_state().value,
                    "model": model.upper(),
                    "source": "windy",
                },
            )
            return None
        except (ConnectionError, Timeout) as e:
            # Errores que el circuit breaker no capturó (ya fueron loggeados en _fetch_with_retry)
            return None
        except Exception as e:
            logger.error(
                "Error en circuit breaker o fetch",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "model": model.upper(),
                    "source": "windy",
                },
                exc_info=True,
            )
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

        # Función interna con retry que será protegida por circuit breaker
        def _fetch_forecast_with_retry() -> List[WeatherData]:
            """Función interna con retry que será protegida por circuit breaker."""
            from app.utils.retry import retry_with_backoff

            @retry_with_backoff(
                max_attempts=3,
                initial_delay=1.0,
                multiplier=2.0,
                max_delay=10.0,
                jitter=True,
                retry_on=(ConnectionError, Timeout),
            )
            def _fetch_data():
                url = f"{self.base_url}"
                payload = {
                    "lat": latitude,
                    "lon": longitude,
                    "model": model,
                    "parameters": self.parameters,
                    "levels": self.levels,
                    "key": self.api_key,
                }

                logger.info(
                    "Obteniendo pronóstico de Windy",
                    extra={
                        "model": model.upper(),
                        "latitude": latitude,
                        "longitude": longitude,
                        "hours": hours,
                        "source": "windy",
                    },
                )
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )

                logger.info(
                    "Windy forecast response recibida",
                    extra={
                        "status_code": response.status_code,
                        "model": model.upper(),
                        "source": "windy",
                    },
                )
                response.raise_for_status()

                data = response.json()
                return data

            try:
                data = _fetch_data()
                forecast = self._extract_forecast(
                    data, latitude, longitude, hours, model
                )

                logger.info(
                    "Pronóstico obtenido",
                    extra={
                        "forecast_points": len(forecast),
                        "model": model.upper(),
                        "source": "windy",
                    },
                )
                return forecast
            except RequestException as e:
                # Errores HTTP (401, 403, 500, etc.) - no retry
                status_code = None
                response_text = None
                if hasattr(e, "response") and e.response is not None:
                    status_code = e.response.status_code
                    response_text = e.response.text[:200] if e.response.text else None

                logger.error(
                    "Error HTTP obteniendo pronóstico de Windy",
                    extra={
                        "error": str(e),
                        "status_code": status_code,
                        "response_preview": response_text,
                        "model": model.upper(),
                        "source": "windy",
                    },
                )
                # No re-raise para errores HTTP (no son transitorios)
                return []
            except Exception as e:
                logger.error(
                    "Error inesperado obteniendo pronóstico",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "model": model.upper(),
                        "source": "windy",
                    },
                    exc_info=True,
                )
                raise  # Re-raise para que circuit breaker lo capture

        # Usar circuit breaker para proteger la llamada
        try:
            return self.circuit_breaker.call(_fetch_forecast_with_retry)
        except CircuitBreakerOpenError as e:
            logger.warning(
                "Circuit breaker abierto para Windy",
                extra={
                    "error": str(e),
                    "circuit_state": self.circuit_breaker.get_state().value,
                    "model": model.upper(),
                    "source": "windy",
                },
            )
            return []
        except (ConnectionError, Timeout) as e:
            # Errores que el circuit breaker no capturó (ya fueron loggeados en _fetch_forecast_with_retry)
            return []
        except Exception as e:
            logger.error(
                "Error en circuit breaker o fetch de pronóstico",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "model": model.upper(),
                    "source": "windy",
                },
                exc_info=True,
            )
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
                logger.warning(
                    f"No se encontraron timestamps en respuesta de Windy ({model}). "
                    f"Claves disponibles: {list(data.keys())[:10]}"
                )
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
            if (
                wind_u_array
                and wind_v_array
                and len(wind_u_array) > 0
                and len(wind_v_array) > 0
            ):
                u = wind_u_array[0]
                v = wind_v_array[0]
                if u is not None and v is not None:
                    wind_speed = (u**2 + v**2) ** 0.5  # Magnitud del vector
                    # Convención meteorológica: dirección DESDE la que sopla el viento (0=N, 90=E, 180=S, 270=O)
                    # Φ = mod(180 + atan2(u, v)°, 360) — u=viento este, v=viento norte
                    wind_direction = (180 + math.degrees(math.atan2(u, v))) % 360

            precipitation = (
                precip_array[0] if precip_array and len(precip_array) > 0 else None
            )

            # Calcular cobertura total de nubes (suma de baja, media y alta)
            cloud_cover = None
            if (
                lclouds_array
                and mclouds_array
                and hclouds_array
                and len(lclouds_array) > 0
                and len(mclouds_array) > 0
                and len(hclouds_array) > 0
            ):
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
            logger.error(
                f"Error extrayendo datos actuales de Windy: {e}", exc_info=True
            )
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
                temperature = (
                    temp_array[i] if temp_array and i < len(temp_array) else None
                )

                # Calcular velocidad y dirección del viento
                wind_speed = None
                wind_direction = None
                if (
                    wind_u_array
                    and wind_v_array
                    and i < len(wind_u_array)
                    and i < len(wind_v_array)
                ):
                    u = wind_u_array[i]
                    v = wind_v_array[i]
                    if u is not None and v is not None:
                        wind_speed = (u**2 + v**2) ** 0.5
                        # Dirección en grados (0 = Norte, 90 = Este, 180 = Sur, 270 = Oeste)
                        wind_direction = (math.degrees(math.atan2(u, v)) + 360) % 360

                precipitation = (
                    precip_array[i] if precip_array and i < len(precip_array) else None
                )

                # Cobertura total de nubes
                cloud_cover = None
                if (
                    lclouds_array
                    and mclouds_array
                    and hclouds_array
                    and i < len(lclouds_array)
                    and i < len(mclouds_array)
                    and i < len(hclouds_array)
                ):
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
