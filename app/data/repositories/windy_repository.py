"""Repositorio para datos de Windy API (ECMWF, GFS, ICON)."""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import requests

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

    # Modelos disponibles en Windy API
    AVAILABLE_MODELS = ["ecmwf", "gfs", "icon"]

    def __init__(self, api_key: Optional[str] = None, default_model: str = "ecmwf"):
        """
        Inicializar repositorio Windy.

        Args:
            api_key: API key de Windy. Si es None, busca en variables de entorno.
            default_model: Modelo por defecto ('ecmwf', 'gfs', 'icon')
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

        try:
            url = f"{self.base_url}"
            params = {
                "lat": latitude,
                "lon": longitude,
                "model": model,
                "key": self.api_key,
            }

            logger.debug(
                f"Obteniendo datos actuales de Windy ({model}) para ({latitude}, {longitude})"
            )
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return self._extract_current_weather(data, latitude, longitude, model)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo datos actuales de Windy: {e}")
            raise WeatherAPIError(f"Error en API Windy: {e}") from e
        except Exception as e:
            logger.error(f"Error inesperado obteniendo datos actuales: {e}")
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

        try:
            url = f"{self.base_url}"
            params = {
                "lat": latitude,
                "lon": longitude,
                "model": model,
                "key": self.api_key,
            }

            logger.debug(
                f"Obteniendo pronóstico de Windy ({model}) para ({latitude}, {longitude}), {hours}h"
            )
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            forecast = self._extract_forecast(data, latitude, longitude, hours, model)

            logger.info(f"Pronóstico obtenido: {len(forecast)} puntos")
            return forecast

        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo pronóstico de Windy: {e}")
            raise WeatherAPIError(f"Error en API Windy: {e}") from e

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
        """Extraer datos actuales de la respuesta de Windy."""
        try:
            # Estructura de respuesta de Windy puede variar
            # Ajustar según documentación oficial
            # Ejemplo de estructura esperada:
            current = (
                data.get("current", {}) or data.get("ts", [{}])[0]
                if data.get("ts")
                else {}
            )

            if not current:
                logger.warning("No se encontraron datos actuales en respuesta de Windy")
                return None

            timestamp_str = current.get("time") or current.get("datetime")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # Extraer variables meteorológicas
            # Ajustar nombres de campos según estructura real de Windy API
            temperature = current.get("temp") or current.get("temperature")
            wind_speed = (
                current.get("windSpeed")
                or current.get("wind_speed")
                or current.get("ws")
            )
            wind_direction = (
                current.get("windDir")
                or current.get("wind_direction")
                or current.get("wd")
            )
            precipitation = (
                current.get("precip")
                or current.get("precipitation")
                or current.get("prcp")
            )
            cloud_cover = (
                current.get("cloudCover")
                or current.get("cloud_cover")
                or current.get("cld")
            )

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
            logger.error(f"Error extrayendo datos actuales de Windy: {e}")
            return None

    def _extract_forecast(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        hours: int,
        model: str,
    ) -> List[WeatherData]:
        """Extraer pronóstico de la respuesta de Windy."""
        forecast = []

        try:
            # Estructura de respuesta puede ser:
            # - data["ts"]: lista de timestamps
            # - data["hourly"]: datos horarios
            # - data["forecast"]: pronóstico
            hourly_data = (
                data.get("ts", [])
                or data.get("hourly", {}).get("data", [])
                or data.get("forecast", [])
            )

            if not hourly_data:
                logger.warning(
                    "No se encontraron datos de pronóstico en respuesta de Windy"
                )
                return forecast

            for item in hourly_data[:hours]:
                weather_data = self._extract_hourly_weather(
                    item, latitude, longitude, model
                )
                if weather_data:
                    forecast.append(weather_data)

        except Exception as e:
            logger.error(f"Error extrayendo pronóstico de Windy: {e}")

        return forecast

    def _extract_hourly_weather(
        self, item: Dict[str, Any], latitude: float, longitude: float, model: str
    ) -> Optional[WeatherData]:
        """Extraer datos horarios de la respuesta de Windy."""
        try:
            timestamp_str = item.get("time") or item.get("datetime") or item.get("date")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(
                        timestamp_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    return None
            else:
                return None

            # Extraer variables meteorológicas
            # Ajustar nombres de campos según estructura real de Windy API
            temperature = item.get("temp") or item.get("temperature")
            wind_speed = (
                item.get("windSpeed") or item.get("wind_speed") or item.get("ws")
            )
            wind_direction = (
                item.get("windDir") or item.get("wind_direction") or item.get("wd")
            )
            precipitation = (
                item.get("precip") or item.get("precipitation") or item.get("prcp")
            )
            cloud_cover = (
                item.get("cloudCover") or item.get("cloud_cover") or item.get("cld")
            )

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
            logger.error(f"Error extrayendo datos horarios de Windy: {e}")
            return None
