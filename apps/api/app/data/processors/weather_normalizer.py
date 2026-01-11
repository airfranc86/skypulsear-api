"""Servicio de normalización de datos meteorológicos."""

import logging
from datetime import UTC, datetime
from typing import Optional

from app.data.schemas.normalized_weather import (
    NormalizedWeatherData,
    WeatherSource,
)
from app.models.weather_data import WeatherData

logger = logging.getLogger(__name__)


class WeatherNormalizerService:
    """Normaliza datos de diferentes fuentes a formato unificado."""

    # Mapeo de nombres de fuente a enum
    SOURCE_MAPPING: dict[str, WeatherSource] = {
        "windy_ecmwf": WeatherSource.WINDY_ECMWF,
        "windy_gfs": WeatherSource.WINDY_GFS,
        "windy_icon": WeatherSource.WINDY_ICON,
        "wrf-smn": WeatherSource.WRF_SMN,
        "wrf_smn": WeatherSource.WRF_SMN,
    }

    def normalize_weather_data(
        self,
        data: WeatherData,
        forecast_hour: int,
        source_override: Optional[str] = None,
    ) -> NormalizedWeatherData:
        """
        Normaliza un WeatherData a NormalizedWeatherData.

        Args:
            data: Datos meteorológicos originales
            forecast_hour: Hora de pronóstico (0=actual)
            source_override: Forzar nombre de fuente

        Returns:
            Datos normalizados
        """
        source_name = source_override or data.source or "unknown"
        source = self._map_source(source_name)

        # CRÍTICO: Convertir temperatura de Kelvin a Celsius ANTES de validar
        # Windy devuelve temperatura en Kelvin (200-350K), debe convertirse a Celsius
        temperature_celsius = None
        if data.temperature is not None:
            temp_raw = float(data.temperature)
            
            # SIEMPRE convertir si > 100 (definitivamente Kelvin)
            if temp_raw > 100:
                temp_celsius = temp_raw - 273.15
                logger.info(f"🌡️ K->°C: {temp_raw:.1f}K = {temp_celsius:.1f}°C")
            else:
                temp_celsius = temp_raw
            
            # Ajustar a límites de Pydantic (-100°C a 60°C)
            if temp_celsius < -100:
                temperature_celsius = -100.0
            elif temp_celsius > 60:
                temperature_celsius = 60.0
            else:
                temperature_celsius = round(temp_celsius, 2)

        return NormalizedWeatherData(
            source=source,
            timestamp=data.timestamp,
            forecast_hour=forecast_hour,
            latitude=data.latitude or 0.0,
            longitude=data.longitude or 0.0,
            temperature_celsius=temperature_celsius,  # Ya convertido y validado
            wind_speed_ms=data.wind_speed,
            wind_direction_deg=data.wind_direction,
            precipitation_mm=data.precipitation,
            cloud_cover_pct=data.cloud_cover,
            humidity_pct=None,  # No disponible en WeatherData básico
            pressure_hpa=None,  # No disponible en WeatherData básico
        )

    def normalize_from_dict(
        self,
        data: dict,
        source: str,
        forecast_hour: int,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherData:
        """
        Normaliza un diccionario a NormalizedWeatherData.

        Args:
            data: Diccionario con datos meteorológicos
            source: Nombre de la fuente
            forecast_hour: Hora de pronóstico
            latitude: Latitud
            longitude: Longitud

        Returns:
            Datos normalizados
        """
        timestamp = self._extract_timestamp(data)
        source_enum = self._map_source(source)

        return NormalizedWeatherData(
            source=source_enum,
            timestamp=timestamp,
            forecast_hour=forecast_hour,
            latitude=latitude,
            longitude=longitude,
            temperature_celsius=self._extract_temperature(data),
            wind_speed_ms=self._extract_wind_speed(data),
            wind_direction_deg=self._extract_wind_direction(data),
            precipitation_mm=self._extract_precipitation(data),
            cloud_cover_pct=self._extract_cloud_cover(data),
            humidity_pct=self._extract_humidity(data),
            pressure_hpa=self._extract_pressure(data),
            raw_data=data,
        )

    def normalize_batch(
        self,
        data_list: list[WeatherData],
        source: str,
        latitude: float,
        longitude: float,
    ) -> list[NormalizedWeatherData]:
        """
        Normaliza una lista de WeatherData.

        Args:
            data_list: Lista de datos meteorológicos
            source: Nombre de la fuente
            latitude: Latitud
            longitude: Longitud

        Returns:
            Lista de datos normalizados
        """
        normalized = []
        base_time = data_list[0].timestamp if data_list else datetime.now(UTC)

        for i, data in enumerate(data_list):
            # Calcular hora de pronóstico basado en diferencia temporal
            hours_diff = int((data.timestamp - base_time).total_seconds() / 3600)
            forecast_hour = max(0, hours_diff)

            # Asignar coordenadas si no están presentes
            if data.latitude is None:
                data.latitude = latitude
            if data.longitude is None:
                data.longitude = longitude

            normalized.append(self.normalize_weather_data(data, forecast_hour, source))

        return normalized

    def _map_source(self, source_name: str) -> WeatherSource:
        """Mapea nombre de fuente a enum."""
        source_lower = source_name.lower().strip()

        # Buscar coincidencia exacta
        if source_lower in self.SOURCE_MAPPING:
            return self.SOURCE_MAPPING[source_lower]

        # Buscar coincidencia parcial
        for key, value in self.SOURCE_MAPPING.items():
            if key in source_lower or source_lower in key:
                return value

        # Default: WRF-SMN (servicio principal)
        logger.warning(f"Fuente desconocida '{source_name}', usando WRF-SMN")
        return WeatherSource.WRF_SMN

    def _extract_timestamp(self, data: dict) -> datetime:
        """Extrae timestamp del diccionario."""
        timestamp = data.get("timestamp") or data.get("time") or data.get("datetime")

        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, str):
            # Intentar parsear ISO format
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                pass

        return datetime.now(UTC)

    def _extract_temperature(self, data: dict) -> Optional[float]:
        """Extrae temperatura en Celsius."""
        temp = (
            data.get("temperature")
            or data.get("temp")
            or data.get("temperature_celsius")
        )
        temp_value = self._to_float(temp)

        # Convertir de Kelvin a Celsius si el valor es > 100 (probablemente Kelvin)
        # Temperaturas en Kelvin típicamente están entre 200-350K
        # Temperaturas en Celsius típicamente están entre -50 y 60°C
        if temp_value is not None:
            original_temp = temp_value
            if temp_value > 100:
                # Asumir que está en Kelvin y convertir a Celsius
                temp_value = temp_value - 273.15
                logger.debug(
                    f"Temperatura convertida de Kelvin a Celsius: {original_temp}K -> {temp_value:.2f}°C"
                )
            # Validar que la temperatura convertida esté en rango razonable
            if temp_value < -100 or temp_value > 100:
                logger.warning(
                    f"Temperatura fuera de rango razonable después de conversión: "
                    f"{temp_value}°C (original: {original_temp}). Ajustando..."
                )
                # Si aún está fuera de rango, puede ser un error de conversión
                if temp_value > 100:
                    temp_value = original_temp - 273.15
                elif temp_value < -100:
                    # Si es muy baja, puede ser que ya estaba en Celsius pero muy fría
                    temp_value = original_temp

        return temp_value

    def _extract_wind_speed(self, data: dict) -> Optional[float]:
        """Extrae velocidad del viento en m/s."""
        wind = data.get("wind_speed") or data.get("wind") or data.get("wind_speed_ms")

        # Convertir de km/h a m/s si es necesario
        value = self._to_float(wind)
        if value is not None and value > 50:  # Probablemente en km/h
            value = value / 3.6

        return value

    def _extract_wind_direction(self, data: dict) -> Optional[float]:
        """Extrae dirección del viento en grados."""
        direction = (
            data.get("wind_direction")
            or data.get("wind_dir")
            or data.get("wind_direction_deg")
        )
        return self._to_float(direction)

    def _extract_precipitation(self, data: dict) -> Optional[float]:
        """Extrae precipitación en mm."""
        precip = (
            data.get("precipitation")
            or data.get("precip")
            or data.get("precipitation_mm")
            or data.get("rain")
        )
        return self._to_float(precip)

    def _extract_cloud_cover(self, data: dict) -> Optional[float]:
        """Extrae cobertura de nubes en porcentaje."""
        clouds = (
            data.get("cloud_cover")
            or data.get("clouds")
            or data.get("cloud_cover_pct")
            or data.get("cloudiness")
        )
        return self._to_float(clouds)

    def _extract_humidity(self, data: dict) -> Optional[float]:
        """Extrae humedad en porcentaje."""
        humidity = (
            data.get("humidity")
            or data.get("humidity_pct")
            or data.get("relative_humidity")
        )
        return self._to_float(humidity)

    def _extract_pressure(self, data: dict) -> Optional[float]:
        """Extrae presión en hPa."""
        pressure = (
            data.get("pressure")
            or data.get("pressure_hpa")
            or data.get("sea_level_pressure")
        )
        return self._to_float(pressure)

    def _to_float(self, value: Optional[any]) -> Optional[float]:
        """Convierte valor a float de forma segura."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
