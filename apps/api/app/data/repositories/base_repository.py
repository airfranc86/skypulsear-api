"""Repositorio base para datos meteorológicos."""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app.models.weather_data import WeatherData


class IWeatherRepository(ABC):
    """Interfaz base para repositorios de datos meteorológicos."""

    @abstractmethod
    def get_current_weather(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherData]:
        """
        Obtener condiciones meteorológicas actuales.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto

        Returns:
            WeatherData con condiciones actuales o None si hay error
        """
        pass

    @abstractmethod
    def get_forecast(
        self, latitude: float, longitude: float, hours: int = 72
    ) -> List[WeatherData]:
        """
        Obtener pronóstico meteorológico.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            hours: Número de horas de pronóstico (default: 72)

        Returns:
            Lista de WeatherData con pronóstico
        """
        pass

    @abstractmethod
    def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> List[WeatherData]:
        """
        Obtener datos históricos.

        Args:
            latitude: Latitud del punto
            longitude: Longitud del punto
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Lista de WeatherData históricos
        """
        pass
