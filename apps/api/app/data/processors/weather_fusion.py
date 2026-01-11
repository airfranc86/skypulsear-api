"""Procesador de fusión de datos meteorológicos."""

import logging
from datetime import datetime
from typing import Optional

from app.data.processors.inconsistency_detector import InconsistencyDetector
from app.data.schemas.normalized_weather import (
    ConfidenceLevel,
    FusionWeights,
    InconsistencyReport,
    NormalizedWeatherData,
    SourceContribution,
    UnifiedForecast,
    WeatherSource,
)

logger = logging.getLogger(__name__)


class WeatherFusionProcessor:
    """Fusiona datos de múltiples fuentes meteorológicas."""

    def __init__(
        self,
        weights: Optional[FusionWeights] = None,
        inconsistency_detector: Optional[InconsistencyDetector] = None,
    ):
        """
        Inicializa el procesador de fusión.

        Args:
            weights: Pesos de fusión personalizados
            inconsistency_detector: Detector de inconsistencias
        """
        self.weights = weights or FusionWeights()
        self.inconsistency_detector = inconsistency_detector or InconsistencyDetector()

    def fuse(
        self,
        data_points: list[NormalizedWeatherData],
        timestamp: datetime,
        forecast_hour: int,
        latitude: float,
        longitude: float,
    ) -> UnifiedForecast:
        """
        Fusiona múltiples fuentes en un pronóstico unificado.

        Args:
            data_points: Lista de datos normalizados de diferentes fuentes
            timestamp: Timestamp del pronóstico
            forecast_hour: Hora de pronóstico (0=actual)
            latitude: Latitud
            longitude: Longitud

        Returns:
            Pronóstico fusionado
        """
        if not data_points:
            return self._create_empty_forecast(
                timestamp, forecast_hour, latitude, longitude
            )

        # Detectar inconsistencias
        inconsistencies = self.inconsistency_detector.detect_inconsistencies(
            data_points, timestamp, forecast_hour
        )

        # Fusionar cada variable
        temp_result = self._fuse_variable(
            data_points, "temperature", forecast_hour, inconsistencies
        )
        wind_result = self._fuse_variable(
            data_points, "wind_speed", forecast_hour, inconsistencies
        )
        precip_result = self._fuse_variable(
            data_points, "precipitation", forecast_hour, inconsistencies
        )

        # Calcular valores adicionales (sin fusión especial)
        wind_dir = self._fuse_wind_direction(data_points)
        cloud_cover = self._simple_average(data_points, "cloud_cover_pct")
        humidity = self._simple_average(data_points, "humidity_pct")
        pressure = self._simple_average(data_points, "pressure_hpa")

        # Calcular confianza global
        confidences = [
            temp_result["confidence"],
            wind_result["confidence"],
            precip_result["confidence"],
        ]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Ajustar confianza por inconsistencias
        significant_inconsistencies = [i for i in inconsistencies if i.is_significant]
        if significant_inconsistencies:
            penalty = min(0.3, len(significant_inconsistencies) * 0.1)
            overall_confidence = max(0.1, overall_confidence - penalty)

        # Determinar nivel de confianza
        confidence_level = self._get_confidence_level(overall_confidence)

        # Obtener fuentes utilizadas
        sources_used = list(set(dp.source for dp in data_points))

        return UnifiedForecast(
            timestamp=timestamp,
            forecast_hour=forecast_hour,
            latitude=latitude,
            longitude=longitude,
            temperature_celsius=temp_result["value"],
            wind_speed_ms=wind_result["value"],
            wind_direction_deg=wind_dir,
            precipitation_mm=precip_result["value"],
            cloud_cover_pct=cloud_cover,
            humidity_pct=humidity,
            pressure_hpa=pressure,
            temperature_confidence=temp_result["confidence"],
            wind_confidence=wind_result["confidence"],
            precipitation_confidence=precip_result["confidence"],
            overall_confidence=overall_confidence,
            confidence_level=confidence_level,
            temperature_contributions=temp_result["contributions"],
            wind_contributions=wind_result["contributions"],
            precipitation_contributions=precip_result["contributions"],
            sources_used=sources_used,
            sources_available=len(data_points),
            inconsistencies=inconsistencies,
            has_significant_inconsistencies=len(significant_inconsistencies) > 0,
            fusion_method="weighted_average",
        )

    def _fuse_variable(
        self,
        data_points: list[NormalizedWeatherData],
        variable: str,
        forecast_hour: int,
        inconsistencies: list[InconsistencyReport],
    ) -> dict:
        """
        Fusiona una variable específica.

        Returns:
            Dict con value, confidence y contributions
        """
        # Obtener pesos base
        base_weights = self.weights.get_weights(variable, forecast_hour)

        # Ajustar pesos por inconsistencias
        adjusted_weights = (
            self.inconsistency_detector.adjust_weights_for_inconsistencies(
                base_weights, inconsistencies
            )
        )

        # Extraer valores por fuente
        source_values: dict[str, float] = {}
        for dp in data_points:
            value = self._get_variable_value(dp, variable)
            if value is not None:
                source_key = self._source_to_weight_key(dp.source)
                source_values[source_key] = value

        if not source_values:
            return {"value": None, "confidence": 0.0, "contributions": []}

        # Calcular valor fusionado
        weighted_sum = 0.0
        total_weight = 0.0
        contributions = []

        for source, value in source_values.items():
            weight = adjusted_weights.get(
                source, 0.1
            )  # Default bajo para fuentes desconocidas
            weighted_sum += value * weight
            total_weight += weight

            contributions.append(
                SourceContribution(
                    source=self._weight_key_to_source(source),
                    value=value,
                    weight=weight,
                    confidence=weight,  # Usar peso como proxy de confianza
                )
            )

        fused_value = weighted_sum / total_weight if total_weight > 0 else None

        # Calcular confianza basada en número de fuentes y consistencia
        base_confidence = min(1.0, len(source_values) / 3)  # Máxima con 3+ fuentes

        # Penalizar si hay inconsistencias para esta variable
        var_inconsistencies = [i for i in inconsistencies if i.variable == variable]
        if var_inconsistencies:
            avg_severity = sum(i.severity for i in var_inconsistencies) / len(
                var_inconsistencies
            )
            base_confidence *= 1 - avg_severity * 0.5

        return {
            "value": round(fused_value, 2) if fused_value is not None else None,
            "confidence": round(base_confidence, 3),
            "contributions": contributions,
        }

    def _fuse_wind_direction(
        self, data_points: list[NormalizedWeatherData]
    ) -> Optional[float]:
        """
        Fusiona dirección del viento usando promedio circular.

        La dirección del viento requiere tratamiento especial
        porque 0° y 360° son el mismo valor.
        """
        import math

        directions = [
            dp.wind_direction_deg
            for dp in data_points
            if dp.wind_direction_deg is not None
        ]

        if not directions:
            return None

        # Convertir a componentes x,y y promediar
        sin_sum = sum(math.sin(math.radians(d)) for d in directions)
        cos_sum = sum(math.cos(math.radians(d)) for d in directions)

        avg_direction = math.degrees(math.atan2(sin_sum, cos_sum))

        # Normalizar a 0-360
        if avg_direction < 0:
            avg_direction += 360

        return round(avg_direction, 1)

    def _simple_average(
        self, data_points: list[NormalizedWeatherData], attribute: str
    ) -> Optional[float]:
        """Calcula promedio simple de un atributo."""
        values = [
            getattr(dp, attribute)
            for dp in data_points
            if getattr(dp, attribute, None) is not None
        ]

        if not values:
            return None

        return round(sum(values) / len(values), 2)

    def _get_variable_value(
        self, data: NormalizedWeatherData, variable: str
    ) -> Optional[float]:
        """Obtiene el valor de una variable."""
        mapping = {
            "temperature": data.temperature_celsius,
            "wind_speed": data.wind_speed_ms,
            "precipitation": data.precipitation_mm,
        }
        return mapping.get(variable)

    def _source_to_weight_key(self, source: WeatherSource) -> str:
        """Convierte enum de fuente a clave de peso."""
        mapping = {
            WeatherSource.WINDY_ECMWF: "windy_ecmwf",
            WeatherSource.WINDY_GFS: "windy_gfs",
            WeatherSource.WINDY_ICON: "windy_gfs",  # ICON usa pesos de GFS
            WeatherSource.WRF_SMN: "wrf_smn",
        }
        return mapping.get(source, "wrf_smn")  # Default: WRF-SMN

    def _weight_key_to_source(self, key: str) -> WeatherSource:
        """Convierte clave de peso a enum de fuente."""
        mapping = {
            "wrf_smn": WeatherSource.WRF_SMN,
            "windy_ecmwf": WeatherSource.WINDY_ECMWF,
            "windy_gfs": WeatherSource.WINDY_GFS,
        }
        return mapping.get(key, WeatherSource.WRF_SMN)  # Default: WRF-SMN

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determina nivel de confianza."""
        if confidence > 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence > 0.7:
            return ConfidenceLevel.HIGH
        elif confidence > 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence > 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _create_empty_forecast(
        self, timestamp: datetime, forecast_hour: int, latitude: float, longitude: float
    ) -> UnifiedForecast:
        """Crea pronóstico vacío cuando no hay datos."""
        return UnifiedForecast(
            timestamp=timestamp,
            forecast_hour=forecast_hour,
            latitude=latitude,
            longitude=longitude,
            overall_confidence=0.0,
            confidence_level=ConfidenceLevel.VERY_LOW,
            sources_available=0,
        )
