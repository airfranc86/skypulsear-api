"""Repositorio para datos de Meteosource API.

Meteosource proporciona acceso a múltiples modelos meteorológicos, incluyendo WRF,
según el plan de suscripción. Para más información sobre modelos disponibles:
https://github.com/Meteosource/pymeteosource
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import requests

from app.data.repositories.base_repository import IWeatherRepository
from app.models.weather_data import WeatherData
from app.utils.exceptions import MeteosourceAPIError
from app.utils.logging_config import get_logger
from app.utils.constants import HTTP_TIMEOUT

logger = get_logger(__name__)


class MeteosourceRepository(IWeatherRepository):
    """
    Repositorio para obtener datos de Meteosource API.

    Meteosource puede proporcionar datos de múltiples modelos meteorológicos,
    incluyendo WRF (Weather Research and Forecasting), según el plan de suscripción.
    La API determina automáticamente el mejor modelo disponible según el plan.

    Referencia: https://github.com/Meteosource/pymeteosource
    """

    def __init__(self, api_key: Optional[str] = None, tier: Optional[str] = None):
        """
        Inicializar repositorio Meteosource.

        Args:
            api_key: API key de Meteosource. Si es None, busca en variables de entorno.
            tier: Plan de suscripción (opcional). Algunos planes incluyen acceso a WRF.
                  Si es None, se usa el tier asociado a la API key.
        """
        self.api_key = api_key or os.getenv("METEOSOURCE_API_KEY")
        if not self.api_key:
            raise ValueError("METEOSOURCE_API_KEY no configurado")

        self.tier = tier or os.getenv("METEOSOURCE_TIER")
        self.base_url = "https://api.meteosource.com/v1/flexi"
        self.timeout = HTTP_TIMEOUT

        # Nota: Meteosource puede usar WRF internamente según el plan
        # El modelo se determina automáticamente por la API
        self._model_info = "Meteosource (puede incluir WRF según plan)"

    def get_current_weather(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherData]:
        """
        Obtener condiciones meteorológicas actuales desde Meteosource.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto

        Returns:
            WeatherData con condiciones actuales o None si hay error
        """
        try:
            url = f"{self.base_url}/point"
            params = {
                "lat": latitude,
                "lon": longitude,
                "key": self.api_key,
                "sections": "current",
                "units": "metric",
                "language": "es",
            }

            logger.debug(
                f"Obteniendo datos actuales de Meteosource para ({latitude}, {longitude})"
            )
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return self._extract_current_weather(data, latitude, longitude)

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout obteniendo datos actuales de Meteosource: {e}")
            return None  # Retornar None en lugar de lanzar excepción
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo datos actuales de Meteosource: {e}")
            return None  # Retornar None para permitir que otras fuentes funcionen
        except Exception as e:
            logger.error(f"Error inesperado obteniendo datos actuales: {e}")
            return None

    def get_forecast(
        self, latitude: float, longitude: float, hours: int = 72
    ) -> List[WeatherData]:
        """
        Obtener pronóstico meteorológico desde Meteosource.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            hours: Número de horas de pronóstico (default: 72)

        Returns:
            Lista de WeatherData con pronóstico
        """
        try:
            url = f"{self.base_url}/point"
            params = {
                "lat": latitude,
                "lon": longitude,
                "key": self.api_key,
                "sections": "hourly",
                "units": "metric",
                "language": "es",
            }

            logger.debug(
                f"Obteniendo pronóstico de Meteosource para ({latitude}, {longitude}), {hours}h"
            )
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            hourly_data = data.get("hourly", {}).get("data", [])

            forecast = []
            for item in hourly_data[:hours]:
                # Pasar data completo para detectar modelo WRF
                weather_data = self._extract_hourly_weather(
                    item, latitude, longitude, data
                )
                if weather_data:
                    forecast.append(weather_data)

            logger.info(f"Pronóstico obtenido: {len(forecast)} puntos")
            return forecast

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout obteniendo pronóstico de Meteosource: {e}")
            return []  # Retornar lista vacía para permitir que otras fuentes funcionen
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo pronóstico de Meteosource: {e}")
            return []  # Retornar lista vacía en lugar de lanzar excepción

    def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> List[WeatherData]:
        """
        Obtener datos históricos desde Meteosource.

        Nota: Disponibilidad según plan de suscripción.

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
                date_str = current_date.strftime("%Y-%m-%d")
                url = f"{self.base_url}/archive"
                params = {
                    "lat": latitude,
                    "lon": longitude,
                    "date": date_str,
                    "key": self.api_key,
                    "units": "metric",
                    "language": "es",
                }

                logger.debug(f"Obteniendo histórico de Meteosource para {date_str}")
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()
                # Procesar datos históricos según estructura de respuesta
                # (ajustar según documentación de Meteosource)

            except requests.exceptions.RequestException as e:
                logger.warning(f"Histórico no disponible para {date_str}: {e}")
                # Continuar con siguiente fecha

            current_date += timedelta(days=1)

        return historical_data

    def _extract_current_weather(
        self, data: Dict[str, Any], latitude: float, longitude: float
    ) -> Optional[WeatherData]:
        """Extraer datos actuales de la respuesta de Meteosource."""
        try:
            current = data.get("current", {})
            if not current:
                return None

            timestamp_str = current.get("time")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            wind = current.get("wind", {})
            precipitation = current.get("precipitation", {})

            # Determinar fuente: Meteosource puede usar WRF según el plan
            source_name = self._get_source_name(data)

            return WeatherData(
                timestamp=timestamp,
                temperature=current.get("temperature"),
                wind_speed=wind.get("speed"),
                wind_direction=wind.get("dir"),
                precipitation=precipitation.get("total"),
                cloud_cover=current.get("cloud_cover"),
                source=source_name,
                latitude=latitude,
                longitude=longitude,
            )
        except Exception as e:
            logger.error(f"Error extrayendo datos actuales: {e}")
            return None

    def _extract_hourly_weather(
        self,
        item: Dict[str, Any],
        latitude: float,
        longitude: float,
        full_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[WeatherData]:
        """
        Extraer datos horarios de la respuesta de Meteosource.

        Args:
            item: Item individual de datos horarios
            latitude: Latitud del punto
            longitude: Longitud del punto
            full_data: Respuesta completa de la API (opcional, para detectar modelo WRF)
        """
        try:
            timestamp_str = item.get("date")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                return None

            wind = item.get("wind", {})
            precipitation = item.get("precipitation", {})

            # Determinar fuente: Meteosource puede usar WRF según el plan
            # Usar full_data si está disponible para mejor detección del modelo
            if full_data:
                source_name = self._get_source_name(full_data)
            else:
                source_name = self._get_source_name_from_item(item)

            return WeatherData(
                timestamp=timestamp,
                temperature=item.get("temperature"),
                wind_speed=wind.get("speed"),
                wind_direction=wind.get("dir"),
                precipitation=precipitation.get("total"),
                cloud_cover=item.get("cloud_cover"),
                source=source_name,
                latitude=latitude,
                longitude=longitude,
            )
        except Exception as e:
            logger.error(f"Error extrayendo datos horarios: {e}")
            return None

    def _get_source_name(self, data: Dict[str, Any]) -> str:
        """
        Determinar el nombre de la fuente basado en la respuesta de la API.

        Meteosource puede usar diferentes modelos (incluyendo WRF) según el plan.
        Si la respuesta incluye información del modelo, se usa; si no, se usa genérico.

        Args:
            data: Respuesta completa de la API

        Returns:
            Nombre de la fuente (ej: "Meteosource (WRF)" o "Meteosource")
        """
        # Intentar detectar el modelo desde la respuesta
        # La estructura puede variar según la versión de la API
        model_info = data.get("model", {})
        if isinstance(model_info, dict):
            model_name = model_info.get("name", "").lower()
            if "wrf" in model_name:
                return "Meteosource (WRF)"

        # Verificar si hay metadata sobre el modelo
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            model = metadata.get("model", "").lower()
            if "wrf" in model:
                return "Meteosource (WRF)"

        # Por defecto, usar nombre genérico
        return "Meteosource"

    def _get_source_name_from_item(self, item: Dict[str, Any]) -> str:
        """
        Determinar el nombre de la fuente desde un item individual.

        Args:
            item: Item individual de datos horarios

        Returns:
            Nombre de la fuente
        """
        # Los items individuales generalmente no incluyen info del modelo
        # Usar el nombre genérico o intentar detectar desde metadata
        model = (
            item.get("model", "").lower() if isinstance(item.get("model"), str) else ""
        )
        if "wrf" in model:
            return "Meteosource (WRF)"

        return "Meteosource"
