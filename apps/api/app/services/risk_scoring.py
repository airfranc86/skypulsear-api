"""Servicio de Risk Scoring por Perfil de Usuario.

Calcula un score de riesgo (0-100) personalizado según el perfil
del usuario y las condiciones meteorológicas.
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.data.schemas.normalized_weather import UnifiedForecast
from app.services.alert_service import AlertLevel, OperationalAlert
from app.services.pattern_detector import DetectedPattern, PatternType, RiskLevel

logger = logging.getLogger(__name__)


class UserProfile(str, Enum):
    """Perfiles de usuario soportados."""

    PILOT = "piloto"
    TRUCKER = "camionero"
    FARMER = "agricultor"
    OUTDOOR_SPORTS = "deporte_aire_libre"
    OUTDOOR_EVENT = "evento_exterior"
    CONSTRUCTION = "construccion"
    TOURISM = "turismo"
    GENERAL = "general"


class RiskCategory(str, Enum):
    """Categorías de riesgo."""

    VERY_LOW = "muy_bajo"
    LOW = "bajo"
    MODERATE = "moderado"
    HIGH = "alto"
    VERY_HIGH = "muy_alto"
    EXTREME = "extremo"


class RiskScore(BaseModel):
    """Score de riesgo calculado."""

    # Score principal (escala 0-5)
    score: float = Field(ge=0, le=5)
    category: RiskCategory

    # Perfil
    profile: UserProfile
    profile_name: str

    # Desglose por factor (0-100 para barras de progreso)
    temperature_risk: int = Field(ge=0, le=100)
    wind_risk: int = Field(ge=0, le=100)
    precipitation_risk: int = Field(ge=0, le=100)
    storm_risk: int = Field(ge=0, le=100, default=0)  # Rayos/tormentas
    hail_risk: int = Field(ge=0, le=100, default=0)  # Granizo
    pattern_risk: int = Field(ge=0, le=100)

    # Máximo riesgo individual
    max_risk: int = Field(ge=0, le=100, default=0)

    # Sensación térmica usada en cálculo
    apparent_temperature: Optional[float] = None

    # Factores principales
    main_risk_factors: list[str] = Field(default_factory=list)

    # Recomendación operativa
    recommendation: str
    action_required: bool = False

    # Ventana temporal
    valid_for_hours: int = 6
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(use_enum_values=True)


class RiskScoringService:
    """
    Servicio de cálculo de riesgo por perfil.

    Cada perfil tiene sensibilidades diferentes a las variables
    meteorológicas, generando scores personalizados.
    """

    # Nombres de perfil en español
    PROFILE_NAMES = {
        UserProfile.PILOT: "Piloto / Aviación",
        UserProfile.TRUCKER: "Transporte / Camionero",
        UserProfile.FARMER: "Agricultura / Campo",
        UserProfile.OUTDOOR_SPORTS: "Deporte al Aire Libre",
        UserProfile.OUTDOOR_EVENT: "Evento al Aire Libre",
        UserProfile.CONSTRUCTION: "Construcción",
        UserProfile.TOURISM: "Turismo / Excursión",
        UserProfile.GENERAL: "General",
    }

    # Pesos por perfil (temperatura, viento, precipitación, patrones)
    # Suma = 1.0 para cada perfil
    PROFILE_WEIGHTS: dict[UserProfile, dict[str, float]] = {
        UserProfile.PILOT: {
            "temperature": 0.10,
            "wind": 0.40,
            "precipitation": 0.25,
            "patterns": 0.25,
        },
        UserProfile.TRUCKER: {
            "temperature": 0.15,
            "wind": 0.30,
            "precipitation": 0.35,
            "patterns": 0.20,
        },
        UserProfile.FARMER: {
            "temperature": 0.30,
            "wind": 0.15,
            "precipitation": 0.30,
            "patterns": 0.25,
        },
        UserProfile.OUTDOOR_SPORTS: {
            "temperature": 0.30,
            "wind": 0.25,
            "precipitation": 0.30,
            "patterns": 0.15,
        },
        UserProfile.OUTDOOR_EVENT: {
            "temperature": 0.20,
            "wind": 0.25,
            "precipitation": 0.35,
            "patterns": 0.20,
        },
        UserProfile.CONSTRUCTION: {
            "temperature": 0.20,
            "wind": 0.35,
            "precipitation": 0.25,
            "patterns": 0.20,
        },
        UserProfile.TOURISM: {
            "temperature": 0.15,
            "wind": 0.15,
            "precipitation": 0.25,
            "patterns": 0.45,  # Descargas eléctricas son críticas para turismo
        },
        UserProfile.GENERAL: {
            "temperature": 0.25,
            "wind": 0.25,
            "precipitation": 0.25,
            "patterns": 0.25,
        },
    }

    # Umbrales por perfil para temperatura (°C)
    TEMP_THRESHOLDS: dict[UserProfile, dict[str, float]] = {
        UserProfile.PILOT: {"cold": 0, "hot": 40, "optimal_min": 5, "optimal_max": 35},
        UserProfile.TRUCKER: {
            "cold": -5,
            "hot": 40,
            "optimal_min": 0,
            "optimal_max": 35,
        },
        UserProfile.FARMER: {
            "cold": 0,
            "hot": 35,
            "optimal_min": 10,
            "optimal_max": 30,
        },
        UserProfile.OUTDOOR_SPORTS: {
            "cold": 5,
            "hot": 32,
            "optimal_min": 10,
            "optimal_max": 26,
        },
        UserProfile.OUTDOOR_EVENT: {
            "cold": 10,
            "hot": 32,
            "optimal_min": 15,
            "optimal_max": 28,
        },
        UserProfile.CONSTRUCTION: {
            "cold": 0,
            "hot": 35,
            "optimal_min": 10,
            "optimal_max": 30,
        },
        UserProfile.TOURISM: {
            "cold": 5,
            "hot": 32,
            "optimal_min": 15,
            "optimal_max": 28,
        },
        UserProfile.GENERAL: {
            "cold": 5,
            "hot": 35,
            "optimal_min": 15,
            "optimal_max": 30,
        },
    }

    # Umbrales de viento por perfil (m/s)
    WIND_THRESHOLDS: dict[UserProfile, dict[str, float]] = {
        UserProfile.PILOT: {"moderate": 8, "strong": 15, "dangerous": 20},
        UserProfile.TRUCKER: {"moderate": 12, "strong": 18, "dangerous": 25},
        UserProfile.FARMER: {"moderate": 10, "strong": 15, "dangerous": 20},
        UserProfile.OUTDOOR_SPORTS: {"moderate": 7, "strong": 11, "dangerous": 16},
        UserProfile.OUTDOOR_EVENT: {"moderate": 8, "strong": 12, "dangerous": 18},
        UserProfile.CONSTRUCTION: {"moderate": 10, "strong": 15, "dangerous": 20},
        UserProfile.TOURISM: {"moderate": 10, "strong": 15, "dangerous": 20},
        UserProfile.GENERAL: {"moderate": 10, "strong": 15, "dangerous": 20},
    }

    # Umbrales de precipitación por perfil (mm)
    PRECIP_THRESHOLDS: dict[UserProfile, dict[str, float]] = {
        UserProfile.PILOT: {"light": 2, "moderate": 5, "heavy": 15},
        UserProfile.TRUCKER: {"light": 5, "moderate": 15, "heavy": 30},
        UserProfile.FARMER: {"light": 10, "moderate": 25, "heavy": 50},
        UserProfile.OUTDOOR_SPORTS: {"light": 1, "moderate": 6, "heavy": 18},
        UserProfile.OUTDOOR_EVENT: {"light": 1, "moderate": 5, "heavy": 15},
        UserProfile.CONSTRUCTION: {"light": 5, "moderate": 15, "heavy": 30},
        UserProfile.TOURISM: {"light": 3, "moderate": 10, "heavy": 25},
        UserProfile.GENERAL: {"light": 5, "moderate": 15, "heavy": 30},
    }

    def calculate_risk(
        self,
        profile: UserProfile,
        forecasts: list[UnifiedForecast],
        patterns: list[DetectedPattern],
        alerts: list[OperationalAlert],
        hours_ahead: int = 6,
    ) -> RiskScore:
        """
        Calcula score de riesgo para un perfil específico.

        Args:
            profile: Perfil de usuario
            forecasts: Pronósticos fusionados
            patterns: Patrones detectados
            alerts: Alertas operativas
            hours_ahead: Horas a considerar (default 6)

        Returns:
            RiskScore con score 0-100 y detalles
        """
        # Filtrar pronósticos por ventana temporal
        relevant_forecasts = [f for f in forecasts if f.forecast_hour <= hours_ahead]

        if not relevant_forecasts:
            relevant_forecasts = forecasts[: max(1, hours_ahead)]

        # Calcular riesgos individuales
        temp_risk, apparent_temp = self._calculate_temperature_risk(
            profile, relevant_forecasts
        )
        wind_risk = self._calculate_wind_risk(profile, relevant_forecasts)
        precip_risk = self._calculate_precipitation_risk(profile, relevant_forecasts)
        storm_risk = self._calculate_storm_risk(relevant_forecasts)
        hail_risk = self._calculate_hail_risk(relevant_forecasts)
        pattern_risk = self._calculate_pattern_risk(profile, patterns, alerts)

        # Obtener pesos del perfil
        weights = self.PROFILE_WEIGHTS[profile]

        # Calcular score ponderado (incluye storm y hail con peso fijo 0.2 cada uno)
        weighted_score = (
            temp_risk * weights["temperature"]
            + wind_risk * weights["wind"]
            + precip_risk * weights["precipitation"]
            + pattern_risk * weights["patterns"]
            + storm_risk * 0.2
            + hail_risk * 0.2
        )

        # Máximo riesgo individual (cualquier factor crítico eleva el índice)
        max_risk = max(
            temp_risk, wind_risk, precip_risk, pattern_risk, storm_risk, hail_risk
        )

        # Combinar: 60% promedio ponderado + 40% máximo individual
        # Esto asegura que una ola de calor sola suba el índice
        combined_score = (weighted_score * 0.6) + (max_risk * 0.4)

        # Convertir de 0-100 a escala 0-5
        final_score = min(5.0, round((combined_score / 100) * 5, 1))

        # Determinar categoría
        category = self._score_to_category(final_score)

        # Identificar factores principales
        risk_factors = self._identify_main_factors(
            temp_risk,
            wind_risk,
            precip_risk,
            pattern_risk,
            storm_risk,
            hail_risk,
            weights,
        )

        # Generar recomendación
        recommendation = self._generate_recommendation(profile, category, risk_factors)

        return RiskScore(
            score=final_score,
            category=category,
            profile=profile,
            profile_name=self.PROFILE_NAMES[profile],
            temperature_risk=round(temp_risk),
            wind_risk=round(wind_risk),
            precipitation_risk=round(precip_risk),
            storm_risk=round(storm_risk),
            hail_risk=round(hail_risk),
            pattern_risk=round(pattern_risk),
            max_risk=round(max_risk),
            apparent_temperature=apparent_temp,
            main_risk_factors=risk_factors,
            recommendation=recommendation,
            action_required=(
                category in [RiskCategory.VERY_HIGH, RiskCategory.EXTREME]
            ),
            valid_for_hours=hours_ahead,
        )

    def calculate_all_profiles(
        self,
        forecasts: list[UnifiedForecast],
        patterns: list[DetectedPattern],
        alerts: list[OperationalAlert],
        hours_ahead: int = 6,
    ) -> dict[UserProfile, RiskScore]:
        """Calcula riesgo para todos los perfiles."""

        results = {}
        for profile in UserProfile:
            results[profile] = self.calculate_risk(
                profile, forecasts, patterns, alerts, hours_ahead
            )
        return results

    def _calculate_temperature_risk(
        self, profile: UserProfile, forecasts: list[UnifiedForecast]
    ) -> tuple[float, Optional[float]]:
        """Calcula riesgo por temperatura usando sensación térmica si disponible.

        Returns:
            tuple: (riesgo 0-100, sensación térmica o None)
        """
        temps = [
            f.temperature_celsius
            for f in forecasts
            if f.temperature_celsius is not None
        ]
        if not temps:
            return 0, None

        # Obtener sensación térmica si existe en el forecast
        apparent_temps = [
            getattr(f, "apparent_temperature", None)
            for f in forecasts
            if getattr(f, "apparent_temperature", None) is not None
        ]

        thresholds = self.TEMP_THRESHOLDS[profile]

        # Usar sensación térmica para calor (el mayor) y frío (el menor)
        max_temp = max(temps)
        min_temp = min(temps)
        apparent_temp = apparent_temps[0] if apparent_temps else None

        # Para calor: usar el valor más alto entre real y sensación
        effective_max_temp = max_temp
        if apparent_temps:
            effective_max_temp = max(max_temp, max(apparent_temps))

        # Para frío: usar el valor más bajo entre real y sensación
        effective_min_temp = min_temp
        if apparent_temps:
            effective_min_temp = min(min_temp, min(apparent_temps))

        risk = 0

        # Riesgo por calor (umbrales más agresivos para olas de calor)
        if effective_max_temp > thresholds["optimal_max"]:
            excess = effective_max_temp - thresholds["optimal_max"]
            hot_range = thresholds["hot"] - thresholds["optimal_max"]
            # Curva más agresiva: 28°C+ ya genera riesgo significativo
            base_risk = min(100, (excess / hot_range) * 100)
            # Bonus por temperaturas extremas (>32°C)
            if effective_max_temp > 32:
                base_risk = min(100, base_risk * 1.3)
            risk = max(risk, base_risk)

        # Riesgo por frío
        if effective_min_temp < thresholds["optimal_min"]:
            deficit = thresholds["optimal_min"] - effective_min_temp
            cold_range = thresholds["optimal_min"] - thresholds["cold"]
            risk = max(risk, min(100, (deficit / cold_range) * 100))

        # Extremos
        if effective_max_temp >= thresholds["hot"]:
            risk = 100
        if effective_min_temp <= thresholds["cold"]:
            risk = max(risk, 90)

        return risk, apparent_temp

    def _calculate_wind_risk(
        self, profile: UserProfile, forecasts: list[UnifiedForecast]
    ) -> float:
        """Calcula riesgo por viento."""

        winds = [f.wind_speed_ms for f in forecasts if f.wind_speed_ms is not None]
        if not winds:
            return 0

        thresholds = self.WIND_THRESHOLDS[profile]
        max_wind = max(winds)

        # Perfiles normales
        if max_wind >= thresholds["dangerous"]:
            return 100
        elif max_wind >= thresholds["strong"]:
            excess = max_wind - thresholds["strong"]
            range_val = thresholds["dangerous"] - thresholds["strong"]
            return 60 + (excess / range_val) * 40
        elif max_wind >= thresholds["moderate"]:
            excess = max_wind - thresholds["moderate"]
            range_val = thresholds["strong"] - thresholds["moderate"]
            return 20 + (excess / range_val) * 40

        return 0

    def _calculate_precipitation_risk(
        self, profile: UserProfile, forecasts: list[UnifiedForecast]
    ) -> float:
        """Calcula riesgo por precipitación."""

        precips = [
            f.precipitation_mm for f in forecasts if f.precipitation_mm is not None
        ]
        if not precips:
            return 0

        thresholds = self.PRECIP_THRESHOLDS[profile]
        total_precip = sum(precips)
        max_precip = max(precips)

        # Usar el máximo entre total acumulado y máximo horario
        effective_precip = max(total_precip / len(precips), max_precip)

        if effective_precip >= thresholds["heavy"]:
            return 100
        elif effective_precip >= thresholds["moderate"]:
            excess = effective_precip - thresholds["moderate"]
            range_val = thresholds["heavy"] - thresholds["moderate"]
            return 50 + (excess / range_val) * 50
        elif effective_precip >= thresholds["light"]:
            excess = effective_precip - thresholds["light"]
            range_val = thresholds["moderate"] - thresholds["light"]
            return 10 + (excess / range_val) * 40

        return 0

    def _calculate_storm_risk(self, forecasts: list[UnifiedForecast]) -> float:
        """Calcula riesgo por tormentas eléctricas/rayos.

        Usa múltiples indicadores:
        1. Weather codes WMO (95, 96, 99) - si están disponibles
        2. Datos de WRF-SMN - precipitación convectiva (RAINC) indica tormentas
        3. Patrones de precipitación + humedad alta - indicador secundario

        Weather codes con tormentas (WMO):
        - 95: Tormenta ligera o moderada
        - 96: Tormenta con granizo ligero
        - 99: Tormenta severa con granizo
        """
        storm_codes = {95, 96, 99}
        max_risk = 0.0

        for forecast in forecasts:
            # Método 1: Weather codes WMO (más confiable si está disponible)
            weather_code = getattr(forecast, "weather_code", None)
            if weather_code in storm_codes:
                if weather_code == 99:
                    return 100.0  # Tormenta severa - riesgo máximo
                elif weather_code == 96:
                    max_risk = max(max_risk, 80.0)  # Tormenta con granizo
                else:
                    max_risk = max(max_risk, 60.0)  # Tormenta normal

            # Método 2: Detección basada en WRF-SMN (precipitación convectiva)
            # WRF-SMN tiene variable RAINC (precipitación convectiva) que es indicador directo
            # Si la fuente es WRF-SMN y hay precipitación, es probable que sea convectiva
            sources = getattr(forecast, "sources_used", [])
            has_wrf_smn = any(
                (
                    source.value == "wrf_smn"
                    if hasattr(source, "value")
                    else source == "wrf_smn"
                )
                for source in sources
            )

            if has_wrf_smn:
                # WRF-SMN con alta precipitación indica tormenta convectiva
                precip = forecast.precipitation_mm or 0.0
                humidity = forecast.humidity_pct or 0.0

                # Precipitación alta (>10mm/h) con humedad alta (>70%) = tormenta probable
                if precip >= 10.0 and humidity >= 70.0:
                    # Escalar riesgo según intensidad de precipitación
                    if precip >= 30.0:
                        max_risk = max(max_risk, 90.0)  # Tormenta severa
                    elif precip >= 20.0:
                        max_risk = max(max_risk, 75.0)  # Tormenta moderada-severa
                    else:
                        max_risk = max(max_risk, 55.0)  # Tormenta moderada

                # Precipitación moderada (5-10mm/h) con condiciones propicias
                elif precip >= 5.0 and humidity >= 75.0:
                    max_risk = max(max_risk, 40.0)  # Riesgo moderado de tormenta

            # Método 3: Indicadores secundarios (precipitación + humedad alta)
            # Aplicar solo si no hay datos de WRF-SMN
            elif not has_wrf_smn:
                precip = forecast.precipitation_mm or 0.0
                humidity = forecast.humidity_pct or 0.0
                temp = forecast.temperature_celsius or 25.0

                # Condiciones propicias para tormentas:
                # - Precipitación alta (>15mm/h)
                # - Humedad muy alta (>80%)
                # - Temperatura moderada-alta (15-35°C)
                if precip >= 15.0 and humidity >= 80.0 and 15.0 <= temp <= 35.0:
                    max_risk = max(max_risk, 50.0)  # Riesgo moderado
                elif precip >= 8.0 and humidity >= 75.0 and 18.0 <= temp <= 32.0:
                    max_risk = max(max_risk, 30.0)  # Riesgo bajo-moderado

        return max_risk

    def _calculate_hail_risk(self, forecasts: list[UnifiedForecast]) -> float:
        """Calcula riesgo de granizo basado en weather_code y temperatura.

        Weather codes con granizo (WMO):
        - 96: Tormenta con granizo ligero
        - 99: Tormenta severa con granizo
        - 77: Granizo (nieve granulada)
        """
        hail_codes = {77, 96, 99}

        for forecast in forecasts:
            weather_code = getattr(forecast, "weather_code", None)
            temp = getattr(forecast, "temperature_celsius", 25)

            if weather_code in hail_codes:
                if weather_code == 99:
                    return 100  # Granizo severo
                elif weather_code == 96:
                    return 70  # Granizo moderado
                else:
                    return 40  # Granizo ligero

            # Condiciones propicias para granizo (tormenta + temp específica)
            if weather_code == 95 and temp is not None:
                if 15 <= temp <= 30:
                    return 30  # Riesgo moderado de granizo

        return 0

    def _calculate_pattern_risk(
        self,
        profile: UserProfile,
        patterns: list[DetectedPattern],
        alerts: list[OperationalAlert],
    ) -> float:
        """Calcula riesgo por patrones y alertas."""

        if not patterns and not alerts:
            return 0

        max_risk = 0

        # Riesgo por patrones
        for pattern in patterns:
            pattern_risk = self._pattern_to_risk(pattern, profile)
            max_risk = max(max_risk, pattern_risk)

        # Riesgo por alertas
        for alert in alerts:
            alert_risk = self._alert_to_risk(alert)
            max_risk = max(max_risk, alert_risk)

        return max_risk

    def _pattern_to_risk(self, pattern: DetectedPattern, profile: UserProfile) -> float:
        """Convierte patrón a riesgo según perfil."""

        base_risk = {
            RiskLevel.LOW: 20,
            RiskLevel.MODERATE: 45,
            RiskLevel.HIGH: 75,
            RiskLevel.EXTREME: 100,
        }.get(pattern.risk_level, 0)

        # Ajustar por tipo de patrón y perfil
        multiplier = 1.0

        # Tormentas severas con descargas eléctricas
        # Aviación: alertas rojas cuando hay descargas en radio 10km del aeropuerto
        # Turismo: riesgo directo por exposición a rayos
        if pattern.pattern_type == PatternType.SEVERE_CONVECTIVE_STORM:
            if profile in [
                UserProfile.PILOT,
                UserProfile.OUTDOOR_EVENT,
                UserProfile.OUTDOOR_SPORTS,
                UserProfile.TOURISM,
            ]:
                multiplier = 1.3
        elif pattern.pattern_type in [PatternType.HEAT_WAVE, PatternType.EXTREME_HEAT]:
            if profile in [
                UserProfile.OUTDOOR_SPORTS,
                UserProfile.CONSTRUCTION,
            ]:
                multiplier = 1.2
        elif pattern.pattern_type in [PatternType.COLD_WAVE, PatternType.FROST]:
            if profile == UserProfile.FARMER:
                multiplier = 1.3

        return min(100, base_risk * multiplier * pattern.confidence)

    def _alert_to_risk(self, alert: OperationalAlert) -> float:
        """Convierte alerta a riesgo."""

        mapping = {
            AlertLevel.NORMAL: 0,
            AlertLevel.ATTENTION: 20,
            AlertLevel.CAUTION: 45,
            AlertLevel.ALERT: 75,
            AlertLevel.CRITICAL: 100,
        }

        return mapping.get(alert.level, 0)

    def _score_to_category(self, score: float) -> RiskCategory:
        """Convierte score (escala 0-5) a categoría."""

        if score >= 4:
            return RiskCategory.EXTREME  # Crítico
        elif score >= 3:
            return RiskCategory.VERY_HIGH  # Alerta
        elif score >= 2:
            return RiskCategory.MODERATE  # Precaución
        elif score >= 1:
            return RiskCategory.LOW  # Atención
        else:
            return RiskCategory.VERY_LOW  # Normal

    def _identify_main_factors(
        self,
        temp_risk: float,
        wind_risk: float,
        precip_risk: float,
        pattern_risk: float,
        storm_risk: float,
        hail_risk: float,
        weights: dict[str, float],
    ) -> list[str]:
        """Identifica los factores de riesgo principales."""

        factors = []

        # Ordenar por contribución al riesgo
        contributions = [
            ("temperatura", temp_risk * weights["temperature"], temp_risk),
            ("viento", wind_risk * weights["wind"], wind_risk),
            ("precipitación", precip_risk * weights["precipitation"], precip_risk),
            ("patrones severos", pattern_risk * weights["patterns"], pattern_risk),
            ("tormentas eléctricas", storm_risk * 0.2, storm_risk),
            ("granizo", hail_risk * 0.2, hail_risk),
        ]

        # Filtrar factores significativos (riesgo base > 30)
        significant = [
            (name, contrib, base) for name, contrib, base in contributions if base > 30
        ]
        significant.sort(key=lambda x: x[1], reverse=True)

        for name, contrib, base in significant[:3]:  # Top 3
            factors.append(name)

        return factors

    def _generate_recommendation(
        self, profile: UserProfile, category: RiskCategory, risk_factors: list[str]
    ) -> str:
        """Genera recomendación personalizada."""

        if category == RiskCategory.VERY_LOW:
            return "Condiciones favorables para su actividad."

        if category == RiskCategory.LOW:
            return "Condiciones aceptables. Monitorear actualizaciones."

        factors_text = (
            ", ".join(risk_factors) if risk_factors else "condiciones meteorológicas"
        )

        # Recomendaciones por perfil y categoría
        if category == RiskCategory.MODERATE:
            base = f"Precaución por {factors_text}."
            specifics = {
                UserProfile.PILOT: " Verificar METAR/TAF antes de operar.",
                UserProfile.FARMER: " Evaluar tareas a campo.",
                UserProfile.OUTDOOR_SPORTS: " Considerar rutas alternativas o postergar.",
                UserProfile.OUTDOOR_EVENT: " Tener plan B disponible.",
            }
            return base + specifics.get(profile, " Evaluar actividad.")

        if category == RiskCategory.HIGH:
            base = f"Riesgo alto por {factors_text}."
            specifics = {
                UserProfile.PILOT: " Reconsiderar operación. Consultar briefing actualizado.",
                UserProfile.TRUCKER: " Evaluar postergar viaje o ruta alternativa.",
                UserProfile.FARMER: " Suspender tareas a campo expuestas.",
                UserProfile.OUTDOOR_SPORTS: " No recomendado salir. Riesgo de accidente.",
                UserProfile.OUTDOOR_EVENT: " Considerar suspensión o traslado.",
            }
            return base + specifics.get(profile, " Modificar o postergar actividad.")

        if category in [RiskCategory.VERY_HIGH, RiskCategory.EXTREME]:
            return f"Riesgo {'extremo' if category == RiskCategory.EXTREME else 'muy alto'}. Evitar actividad al aire libre. Priorizar seguridad."

        return "Evaluar condiciones antes de proceder."
