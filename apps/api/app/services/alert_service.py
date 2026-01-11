"""Sistema de Alertas Operativas SkyPulse.

Traduce información meteorológica técnica en niveles de alerta claros,
confiables y accionables, alineados con la estructura del SMN.

NO reemplaza alertas oficiales - es una interpretación operativa.
"""

import logging
from datetime import UTC, datetime, timedelta
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.data.schemas.normalized_weather import UnifiedForecast
from app.services.pattern_detector import DetectedPattern, PatternType, RiskLevel

logger = logging.getLogger(__name__)


class AlertLevel(IntEnum):
    """Niveles de Alerta SkyPulse (0-4)."""

    NORMAL = 0  # Condición Normal
    ATTENTION = 1  # Atención
    CAUTION = 2  # Precaución
    ALERT = 3  # Alerta
    CRITICAL = 4  # Alerta Crítica


class AlertPhenomenon(str):
    """Fenómenos meteorológicos alertables."""

    THUNDERSTORM = "tormentas"
    SEVERE_THUNDERSTORM = "tormentas severas"
    HAIL = "granizo"
    STRONG_WIND = "vientos fuertes"
    HEAVY_RAIN = "lluvia intensa"
    HEAT_WAVE = "ola de calor"
    COLD_WAVE = "ola de frío"
    FROST = "heladas"
    EXTREME_HEAT = "calor extremo"
    REDUCED_VISIBILITY = "visibilidad reducida"


class OperationalAlert(BaseModel):
    """Alerta Operativa SkyPulse."""

    # Nivel y clasificación
    level: AlertLevel
    level_name: str

    # Fenómeno
    phenomenon: str
    description: str

    # Temporalidad
    time_window: str  # Ej: "16–20 h"
    horizon_hours: int  # Horizonte en horas
    proximity: Optional[str] = None  # Ej: "actividad convectiva a 50 km"

    # Impacto y acción
    expected_impact: list[str] = Field(default_factory=list)
    recommendation: str

    # Metadata
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    # Fuentes
    source_note: str = (
        "Interpretación operativa basada en fuentes oficiales (SMN, GOES-16, radar, WRF-SMN)"
    )

    model_config = ConfigDict(use_enum_values=True)

    def to_display_format(self) -> str:
        """Formato de salida para display."""
        lines = [
            f"Nivel: {self.level_name}",
            f"Fenómeno: {self.phenomenon}",
            f"Ventana estimada: {self.time_window}",
        ]

        if self.proximity:
            lines.append(f"Proximidad: {self.proximity}")

        if self.expected_impact:
            lines.append(f"Impacto: {', '.join(self.expected_impact)}")

        lines.append(f"Recomendación: {self.recommendation}")
        lines.append(f"\n{self.source_note}")

        return "\n".join(lines)


class AlertService:
    """
    Servicio de Alertas Operativas SkyPulse.

    Genera alertas basadas en:
    - Patrones detectados (PatternDetector)
    - Pronósticos fusionados (UnifiedForecast)
    - Umbrales configurables
    """

    # Mensajes por nivel
    LEVEL_MESSAGES = {
        AlertLevel.NORMAL: "Condiciones estables. Sin impacto operativo esperado.",
        AlertLevel.ATTENTION: "Escenario en evolución. Condiciones a monitorear. Sin acción requerida por ahora.",
        AlertLevel.CAUTION: "Riesgo moderado. Posibles interrupciones según actividad.",
        AlertLevel.ALERT: "Riesgo alto. Se recomienda modificar o evitar actividades sensibles.",
        AlertLevel.CRITICAL: "Condición peligrosa confirmada. Evitar actividades al aire libre.",
    }

    LEVEL_NAMES = {
        AlertLevel.NORMAL: "Condición Normal",
        AlertLevel.ATTENTION: "Atención",
        AlertLevel.CAUTION: "Precaución",
        AlertLevel.ALERT: "Alerta",
        AlertLevel.CRITICAL: "Alerta Crítica",
    }

    # Horizontes temporales por nivel (horas)
    HORIZONS = {
        AlertLevel.NORMAL: (24, 72),
        AlertLevel.ATTENTION: (24, 48),
        AlertLevel.CAUTION: (12, 24),
        AlertLevel.ALERT: (3, 12),
        AlertLevel.CRITICAL: (0, 3),
    }

    def generate_alerts(
        self,
        patterns: list[DetectedPattern],
        forecasts: list[UnifiedForecast],
        current_time: Optional[datetime] = None,
    ) -> list[OperationalAlert]:
        """
        Genera alertas operativas basadas en patrones y pronósticos.

        Args:
            patterns: Patrones detectados
            forecasts: Pronósticos fusionados
            current_time: Hora actual (default: now)

        Returns:
            Lista de alertas operativas ordenadas por nivel (mayor primero)
        """
        current_time = current_time or datetime.now(UTC)
        alerts: list[OperationalAlert] = []

        # Generar alertas desde patrones detectados
        for pattern in patterns:
            alert = self._pattern_to_alert(pattern, current_time)
            if alert:
                alerts.append(alert)

        # Analizar pronósticos para alertas adicionales
        forecast_alerts = self._analyze_forecasts(forecasts, current_time)
        alerts.extend(forecast_alerts)

        # Eliminar duplicados y ordenar por nivel (mayor primero)
        alerts = self._deduplicate_alerts(alerts)
        alerts.sort(key=lambda a: a.level, reverse=True)

        # Si no hay alertas, generar nivel 0
        if not alerts:
            alerts.append(self._create_normal_alert(current_time))

        logger.info(f"Generadas {len(alerts)} alertas operativas")
        return alerts

    def get_max_alert_level(self, patterns: list[DetectedPattern]) -> AlertLevel:
        """Obtiene el nivel máximo de alerta de los patrones."""
        if not patterns:
            return AlertLevel.NORMAL

        max_level = AlertLevel.NORMAL

        for pattern in patterns:
            level = self._risk_to_alert_level(pattern.risk_level, pattern.confidence)
            if level > max_level:
                max_level = level

        return max_level

    def _pattern_to_alert(
        self, pattern: DetectedPattern, current_time: datetime
    ) -> Optional[OperationalAlert]:
        """Convierte un patrón detectado en alerta operativa."""

        # Determinar nivel de alerta
        level = self._risk_to_alert_level(pattern.risk_level, pattern.confidence)

        if level == AlertLevel.NORMAL:
            return None

        # Determinar fenómeno y detalles según tipo de patrón
        phenomenon, impacts = self._get_phenomenon_details(pattern)

        # Calcular ventana temporal
        horizon_min, horizon_max = self.HORIZONS[level]
        time_window = self._calculate_time_window(
            current_time, horizon_min, horizon_max
        )

        # Generar proximidad si aplica
        proximity = self._get_proximity_text(pattern, level)

        # Generar recomendación específica
        recommendation = self._get_recommendation(pattern, level)

        return OperationalAlert(
            level=level,
            level_name=self.LEVEL_NAMES[level],
            phenomenon=phenomenon,
            description=pattern.description,
            time_window=time_window,
            horizon_hours=horizon_max,
            proximity=proximity,
            expected_impact=impacts,
            recommendation=recommendation,
            valid_from=current_time,
            valid_until=current_time + timedelta(hours=horizon_max),
        )

    def _analyze_forecasts(
        self, forecasts: list[UnifiedForecast], current_time: datetime
    ) -> list[OperationalAlert]:
        """Analiza pronósticos para generar alertas adicionales."""
        alerts = []

        if not forecasts:
            return alerts

        # Agrupar por ventanas temporales
        windows = {
            "0-3h": [f for f in forecasts if f.forecast_hour <= 3],
            "3-12h": [f for f in forecasts if 3 < f.forecast_hour <= 12],
            "12-24h": [f for f in forecasts if 12 < f.forecast_hour <= 24],
            "24-48h": [f for f in forecasts if 24 < f.forecast_hour <= 48],
        }

        # Analizar cada ventana
        for window_name, window_forecasts in windows.items():
            if not window_forecasts:
                continue

            # Verificar condiciones de alerta
            alert = self._check_window_conditions(
                window_forecasts, window_name, current_time
            )
            if alert:
                alerts.append(alert)

        return alerts

    def _check_window_conditions(
        self, forecasts: list[UnifiedForecast], window_name: str, current_time: datetime
    ) -> Optional[OperationalAlert]:
        """Verifica condiciones de alerta en una ventana temporal."""

        # Extraer máximos
        max_precip = max((f.precipitation_mm or 0 for f in forecasts), default=0)
        max_wind = max((f.wind_speed_ms or 0 for f in forecasts), default=0)
        max_temp = max((f.temperature_celsius or 0 for f in forecasts), default=0)
        min_temp = min((f.temperature_celsius or 100 for f in forecasts), default=100)

        # Determinar nivel según ventana y condiciones
        level = AlertLevel.NORMAL
        phenomenon = ""
        impacts = []

        # Precipitación intensa
        if max_precip >= 30:
            if window_name == "0-3h":
                level = max(level, AlertLevel.CRITICAL)
            elif window_name == "3-12h":
                level = max(level, AlertLevel.ALERT)
            else:
                level = max(level, AlertLevel.CAUTION)
            phenomenon = "lluvia intensa"
            impacts.append(f"precipitación de hasta {max_precip:.0f}mm")

        # Vientos fuertes
        if max_wind >= 20:  # ~72 km/h
            if window_name == "0-3h":
                level = max(level, AlertLevel.ALERT)
            elif window_name == "3-12h":
                level = max(level, AlertLevel.CAUTION)
            else:
                level = max(level, AlertLevel.ATTENTION)
            phenomenon = phenomenon or "vientos fuertes"
            impacts.append(f"ráfagas de hasta {max_wind * 3.6:.0f} km/h")

        # Calor extremo
        if max_temp >= 40:
            level = max(level, AlertLevel.ALERT)
            phenomenon = phenomenon or "calor extremo"
            impacts.append(f"temperatura máxima de {max_temp:.0f}°C")

        # Heladas
        if min_temp <= 0:
            if window_name in ["0-3h", "3-12h"]:
                level = max(level, AlertLevel.ALERT)
            else:
                level = max(level, AlertLevel.CAUTION)
            phenomenon = phenomenon or "heladas"
            impacts.append(f"temperatura mínima de {min_temp:.0f}°C")

        if level == AlertLevel.NORMAL:
            return None

        # Calcular ventana horaria
        time_window = self._window_name_to_time(window_name, current_time)

        return OperationalAlert(
            level=level,
            level_name=self.LEVEL_NAMES[level],
            phenomenon=phenomenon,
            description=f"Condiciones adversas previstas: {', '.join(impacts)}",
            time_window=time_window,
            horizon_hours=int(window_name.split("-")[1].replace("h", "")),
            expected_impact=impacts,
            recommendation=self._get_generic_recommendation(level),
            valid_from=current_time,
        )

    def _risk_to_alert_level(self, risk: RiskLevel, confidence: float) -> AlertLevel:
        """Convierte nivel de riesgo a nivel de alerta."""

        # Mapeo base
        base_mapping = {
            RiskLevel.LOW: AlertLevel.ATTENTION,
            RiskLevel.MODERATE: AlertLevel.CAUTION,
            RiskLevel.HIGH: AlertLevel.ALERT,
            RiskLevel.EXTREME: AlertLevel.CRITICAL,
        }

        level = base_mapping.get(risk, AlertLevel.NORMAL)

        # Ajustar por confianza baja
        if confidence < 0.5 and level > AlertLevel.ATTENTION:
            level = AlertLevel(level - 1)

        return level

    def _get_phenomenon_details(
        self, pattern: DetectedPattern
    ) -> tuple[str, list[str]]:
        """Obtiene fenómeno e impactos según tipo de patrón."""

        mapping = {
            PatternType.SEVERE_CONVECTIVE_STORM: (
                "tormentas severas",
                [
                    "ráfagas fuertes",
                    "lluvia intensa",
                    "posible granizo",
                    "actividad eléctrica",
                ],
            ),
            PatternType.HEAT_WAVE: (
                "ola de calor",
                [
                    "temperaturas elevadas sostenidas",
                    "estrés térmico",
                    "riesgo para salud",
                ],
            ),
            PatternType.COLD_WAVE: (
                "ola de frío",
                [
                    "temperaturas bajas sostenidas",
                    "riesgo de hipotermia",
                    "posibles heladas",
                ],
            ),
            PatternType.FROST: (
                "heladas",
                ["formación de hielo", "daño a cultivos", "superficies resbaladizas"],
            ),
            PatternType.EXTREME_HEAT: (
                "calor extremo",
                ["temperatura peligrosa", "golpe de calor", "deshidratación"],
            ),
        }

        return mapping.get(
            pattern.pattern_type, ("fenómeno meteorológico", ["condiciones adversas"])
        )

    def _calculate_time_window(
        self, current_time: datetime, horizon_min: int, horizon_max: int
    ) -> str:
        """Calcula ventana temporal legible."""

        start = current_time + timedelta(hours=horizon_min)
        end = current_time + timedelta(hours=horizon_max)

        # Formato según horizonte
        if horizon_max <= 3:
            return f"próximas {horizon_max} horas"
        elif horizon_max <= 12:
            return f"{start.strftime('%H')}–{end.strftime('%H')} h"
        elif horizon_max <= 24:
            if start.date() == end.date():
                return f"hoy {start.strftime('%H')}–{end.strftime('%H')} h"
            else:
                return f"hoy tarde/noche"
        else:
            return f"próximas {horizon_max} h"

    def _window_name_to_time(self, window_name: str, current_time: datetime) -> str:
        """Convierte nombre de ventana a texto temporal."""

        mapping = {
            "0-3h": "próximas 3 horas",
            "3-12h": f"{(current_time + timedelta(hours=3)).strftime('%H')}–{(current_time + timedelta(hours=12)).strftime('%H')} h",
            "12-24h": "próximas 12–24 h",
            "24-48h": "mañana",
        }

        return mapping.get(window_name, window_name)

    def _get_proximity_text(
        self, pattern: DetectedPattern, level: AlertLevel
    ) -> Optional[str]:
        """Genera texto de proximidad si aplica."""

        if level < AlertLevel.ALERT:
            return None

        if pattern.pattern_type == PatternType.SEVERE_CONVECTIVE_STORM:
            if level == AlertLevel.CRITICAL:
                return "actividad convectiva detectada, posible impacto < 1 hora"
            else:
                return "desarrollo convectivo en la región"

        return None

    def _get_recommendation(self, pattern: DetectedPattern, level: AlertLevel) -> str:
        """Genera recomendación específica según patrón y nivel."""

        # Usar recomendaciones del patrón si existen
        if pattern.recommendations:
            # Seleccionar según nivel
            if level >= AlertLevel.ALERT and len(pattern.recommendations) > 2:
                return pattern.recommendations[0]  # Más urgente
            elif pattern.recommendations:
                return pattern.recommendations[0]

        return self._get_generic_recommendation(level)

    def _get_generic_recommendation(self, level: AlertLevel) -> str:
        """Recomendación genérica por nivel."""

        recommendations = {
            AlertLevel.NORMAL: "Sin acción requerida.",
            AlertLevel.ATTENTION: "Monitorear actualizaciones meteorológicas.",
            AlertLevel.CAUTION: "Evaluar planes y monitorear actualizaciones.",
            AlertLevel.ALERT: "Modificar o postergar actividades sensibles al clima.",
            AlertLevel.CRITICAL: "Evitar actividades al aire libre. Buscar refugio seguro.",
        }

        return recommendations.get(level, "Mantenerse informado.")

    def _create_normal_alert(self, current_time: datetime) -> OperationalAlert:
        """Crea alerta de nivel 0 (normal)."""

        return OperationalAlert(
            level=AlertLevel.NORMAL,
            level_name=self.LEVEL_NAMES[AlertLevel.NORMAL],
            phenomenon="condiciones estables",
            description="Sin fenómenos meteorológicos significativos previstos.",
            time_window="próximas 24–72 h",
            horizon_hours=72,
            expected_impact=[],
            recommendation="Sin acción requerida.",
            valid_from=current_time,
            valid_until=current_time + timedelta(hours=72),
        )

    def _deduplicate_alerts(
        self, alerts: list[OperationalAlert]
    ) -> list[OperationalAlert]:
        """Elimina alertas duplicadas, manteniendo la de mayor nivel."""

        seen_phenomena: dict[str, OperationalAlert] = {}

        for alert in alerts:
            key = alert.phenomenon
            if key not in seen_phenomena or alert.level > seen_phenomena[key].level:
                seen_phenomena[key] = alert

        return list(seen_phenomena.values())
