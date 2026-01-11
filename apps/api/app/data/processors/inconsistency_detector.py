"""Detector de inconsistencias entre fuentes meteorológicas."""

import logging
from datetime import datetime
from statistics import mean, stdev
from typing import Optional

from app.data.schemas.normalized_weather import (
    InconsistencyReport,
    NormalizedWeatherData,
)

logger = logging.getLogger(__name__)


class InconsistencyDetector:
    """Detecta inconsistencias entre múltiples fuentes de datos."""

    # Umbrales de inconsistencia por variable
    THRESHOLDS: dict[str, dict[str, float]] = {
        "temperature": {
            "max_std": 3.0,  # °C - desviación estándar máxima aceptable
            "max_range": 8.0,  # °C - rango máximo aceptable
            "outlier_factor": 2.0,  # Factor para detectar outliers (n * std)
        },
        "wind_speed": {
            "max_std": 4.0,  # m/s
            "max_range": 10.0,  # m/s
            "outlier_factor": 2.0,
        },
        "precipitation": {
            "max_std": 5.0,  # mm
            "max_range": 15.0,  # mm
            "outlier_factor": 2.5,  # Mayor tolerancia para precipitación
        },
        "cloud_cover": {
            "max_std": 20.0,  # %
            "max_range": 50.0,  # %
            "outlier_factor": 2.0,
        },
    }

    def detect_inconsistencies(
        self,
        data_points: list[NormalizedWeatherData],
        timestamp: datetime,
        forecast_hour: int,
    ) -> list[InconsistencyReport]:
        """
        Detecta inconsistencias en un conjunto de datos.

        Args:
            data_points: Lista de datos normalizados de diferentes fuentes
            timestamp: Timestamp del pronóstico
            forecast_hour: Hora de pronóstico

        Returns:
            Lista de reportes de inconsistencia
        """
        if len(data_points) < 2:
            return []

        reports = []

        # Analizar cada variable
        for variable in ["temperature", "wind_speed", "precipitation", "cloud_cover"]:
            report = self._analyze_variable(
                data_points, variable, timestamp, forecast_hour
            )
            if (
                report and report.severity > 0.1
            ):  # Solo reportar si hay alguna inconsistencia
                reports.append(report)

        return reports

    def _analyze_variable(
        self,
        data_points: list[NormalizedWeatherData],
        variable: str,
        timestamp: datetime,
        forecast_hour: int,
    ) -> Optional[InconsistencyReport]:
        """Analiza inconsistencias para una variable específica."""
        # Extraer valores por fuente
        source_values: dict[str, float] = {}

        for dp in data_points:
            value = self._get_variable_value(dp, variable)
            if value is not None:
                source_values[dp.source] = value

        if len(source_values) < 2:
            return None

        values = list(source_values.values())

        # Calcular estadísticas
        mean_val = mean(values)
        std_val = stdev(values) if len(values) > 1 else 0.0
        max_val = max(values)
        min_val = min(values)
        max_deviation = max_val - min_val

        # Coeficiente de variación (evitar división por cero)
        cv = (std_val / abs(mean_val)) if mean_val != 0 else 0.0

        # Detectar outliers
        thresholds = self.THRESHOLDS.get(variable, self.THRESHOLDS["temperature"])
        outlier_sources = self._find_outliers(
            source_values, mean_val, std_val, thresholds["outlier_factor"]
        )

        # Calcular severidad (0-1)
        severity = self._calculate_severity(std_val, max_deviation, cv, thresholds)

        return InconsistencyReport(
            variable=variable,
            timestamp=timestamp,
            forecast_hour=forecast_hour,
            source_values=source_values,
            mean_value=mean_val,
            std_deviation=std_val,
            max_deviation=max_deviation,
            coefficient_of_variation=cv,
            outlier_sources=outlier_sources,
            severity=severity,
        )

    def _get_variable_value(
        self, data: NormalizedWeatherData, variable: str
    ) -> Optional[float]:
        """Obtiene el valor de una variable del dato normalizado."""
        mapping = {
            "temperature": data.temperature_celsius,
            "wind_speed": data.wind_speed_ms,
            "precipitation": data.precipitation_mm,
            "cloud_cover": data.cloud_cover_pct,
        }
        return mapping.get(variable)

    def _find_outliers(
        self,
        source_values: dict[str, float],
        mean_val: float,
        std_val: float,
        outlier_factor: float,
    ) -> list[str]:
        """Identifica fuentes con valores outliers."""
        if std_val == 0:
            return []

        outliers = []
        threshold = outlier_factor * std_val

        for source, value in source_values.items():
            if abs(value - mean_val) > threshold:
                outliers.append(source)

        return outliers

    def _calculate_severity(
        self,
        std_val: float,
        max_deviation: float,
        cv: float,
        thresholds: dict[str, float],
    ) -> float:
        """
        Calcula severidad de inconsistencia (0-1).

        Combina múltiples métricas para determinar qué tan grave
        es la inconsistencia entre fuentes.
        """
        # Componente por desviación estándar
        std_severity = min(1.0, std_val / thresholds["max_std"])

        # Componente por rango
        range_severity = min(1.0, max_deviation / thresholds["max_range"])

        # Componente por coeficiente de variación
        cv_severity = min(1.0, cv / 0.5)  # CV > 0.5 = máxima severidad

        # Promedio ponderado
        severity = 0.4 * std_severity + 0.4 * range_severity + 0.2 * cv_severity

        return round(min(1.0, severity), 3)

    def adjust_weights_for_inconsistencies(
        self, base_weights: dict[str, float], inconsistencies: list[InconsistencyReport]
    ) -> dict[str, float]:
        """
        Ajusta pesos basándose en inconsistencias detectadas.

        Reduce el peso de fuentes que son outliers consistentes.

        Args:
            base_weights: Pesos originales por fuente
            inconsistencies: Lista de inconsistencias detectadas

        Returns:
            Pesos ajustados
        """
        adjusted = base_weights.copy()

        # Contar cuántas veces cada fuente es outlier
        outlier_counts: dict[str, int] = {}
        for report in inconsistencies:
            for source in report.outlier_sources:
                outlier_counts[source] = outlier_counts.get(source, 0) + 1

        # Reducir peso de fuentes problemáticas
        for source, count in outlier_counts.items():
            if source in adjusted:
                # Reducir peso proporcionalmente al número de inconsistencias
                reduction_factor = max(0.5, 1.0 - (count * 0.1))
                adjusted[source] *= reduction_factor

        # Renormalizar pesos para que sumen 1
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}

        return adjusted
