"""Repositorio para datos de estaciones meteorológicas locales."""

import os
from typing import List, Optional
from datetime import datetime
import pandas as pd

from app.data.repositories.base_repository import IWeatherRepository
from app.models.weather_data import WeatherData
from app.utils.exceptions import RepositoryError, DataValidationError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class LocalStationsRepository(IWeatherRepository):
    """Repositorio para obtener datos de estaciones meteorológicas locales (CSV)."""

    def __init__(self, csv_path: Optional[str] = None):
        """
        Inicializar repositorio de estaciones locales.

        Args:
            csv_path: Ruta al archivo CSV. Si es None, busca en variables de entorno.
        """
        self.csv_path = csv_path or os.getenv("LOCAL_STATIONS_PATH", "StationCba.csv")
        self._data: Optional[pd.DataFrame] = None

    def _load_data(self) -> pd.DataFrame:
        """
        Cargar datos del CSV.

        Returns:
            DataFrame con datos de estaciones

        Raises:
            RepositoryError: Si no se puede cargar el archivo
            DataValidationError: Si el formato del CSV es incorrecto
        """
        if self._data is not None:
            return self._data

        try:
            logger.info(f"Cargando datos de estaciones locales desde {self.csv_path}")
            df = pd.read_csv(self.csv_path)

            # Validar columnas requeridas
            required_columns = [
                "timestamp",
                "temp",
                "viento_vel",
                "viento_dir",
                "precip",
                "nubosidad",
            ]
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise DataValidationError(
                    f"Columnas faltantes en CSV: {missing_columns}. "
                    f"Columnas requeridas: {required_columns}"
                )

            # Convertir timestamp
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Validar que no esté vacío
            if df.empty:
                raise DataValidationError("El archivo CSV está vacío")

            self._data = df
            logger.info(f"Datos cargados: {len(df)} registros")
            return df

        except FileNotFoundError:
            error_msg = f"Archivo no encontrado: {self.csv_path}"
            logger.warning(error_msg)
            # Retornar DataFrame vacío en lugar de lanzar excepción
            return pd.DataFrame()
        except pd.errors.EmptyDataError:
            error_msg = f"El archivo CSV está vacío: {self.csv_path}"
            logger.error(error_msg)
            raise DataValidationError(error_msg) from None
        except Exception as e:
            error_msg = f"Error cargando datos de estaciones: {e}"
            logger.error(error_msg)
            raise RepositoryError(error_msg) from e

    def get_current_weather(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherData]:
        """
        Obtener condiciones meteorológicas actuales (más recientes).

        Args:
            latitude: Latitud (no usado para CSV, pero requerido por interfaz)
            longitude: Longitud (no usado para CSV, pero requerido por interfaz)

        Returns:
            WeatherData más reciente o None si no hay datos
        """
        try:
            df = self._load_data()
            if df.empty:
                return None

            # Obtener registro más reciente
            latest = df.iloc[-1]

            return WeatherData(
                timestamp=latest["timestamp"],
                temperature=latest.get("temp"),
                wind_speed=latest.get("viento_vel"),
                wind_direction=latest.get("viento_dir"),
                precipitation=latest.get("precip"),
                cloud_cover=latest.get("nubosidad"),
                source="Estación Local",
                latitude=latitude,
                longitude=longitude,
            )
        except Exception as e:
            logger.error(f"Error obteniendo datos actuales de estaciones: {e}")
            return None

    def get_forecast(
        self, latitude: float, longitude: float, hours: int = 72
    ) -> List[WeatherData]:
        """
        Las estaciones locales no proporcionan pronóstico.

        Returns:
            Lista vacía
        """
        logger.warning("Las estaciones locales no proporcionan pronóstico")
        return []

    def get_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
    ) -> List[WeatherData]:
        """
        Obtener datos históricos del CSV.

        Args:
            latitude: Latitud
            longitude: Longitud
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Lista de WeatherData históricos
        """
        try:
            df = self._load_data()

            # Filtrar por rango de fechas
            mask = (df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)
            filtered_df = df[mask]

            historical = []
            for _, row in filtered_df.iterrows():
                weather_data = WeatherData(
                    timestamp=row["timestamp"],
                    temperature=row.get("temp"),
                    wind_speed=row.get("viento_vel"),
                    wind_direction=row.get("viento_dir"),
                    precipitation=row.get("precip"),
                    cloud_cover=row.get("nubosidad"),
                    source="Estación Local",
                    latitude=latitude,
                    longitude=longitude,
                )
                historical.append(weather_data)

            logger.info(f"Datos históricos obtenidos: {len(historical)} registros")
            return historical

        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            return []

    def get_weather_near_timestamp(
        self, timestamp: datetime, window_minutes: int = 15
    ) -> Optional[WeatherData]:
        """
        Obtener datos cercanos a un timestamp específico.

        Args:
            timestamp: Timestamp objetivo
            window_minutes: Ventana de tiempo en minutos (default: 15)

        Returns:
            WeatherData más cercano al timestamp o None
        """
        try:
            df = self._load_data()

            # Calcular ventana de tiempo
            window = pd.Timedelta(minutes=window_minutes)
            mask = df["timestamp"].between(timestamp - window, timestamp + window)
            filtered_df = df[mask]

            if filtered_df.empty:
                logger.warning(
                    f"No hay datos cercanos a {timestamp} (±{window_minutes} min)"
                )
                return None

            # Obtener el más cercano
            filtered_df["time_diff"] = (filtered_df["timestamp"] - timestamp).abs()
            closest = filtered_df.loc[filtered_df["time_diff"].idxmin()]

            return WeatherData(
                timestamp=closest["timestamp"],
                temperature=closest.get("temp"),
                wind_speed=closest.get("viento_vel"),
                wind_direction=closest.get("viento_dir"),
                precipitation=closest.get("precip"),
                cloud_cover=closest.get("nubosidad"),
                source="Estación Local",
                latitude=None,
                longitude=None,
            )
        except Exception as e:
            logger.error(f"Error obteniendo datos cercanos a timestamp: {e}")
            return None
