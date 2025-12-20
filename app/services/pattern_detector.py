"""Detector de Patrones Meteorológicos Argentinos."""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.data.schemas.normalized_weather import NormalizedWeatherData, UnifiedForecast

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Tipos de patrones meteorológicos detectables."""
    
    SEVERE_CONVECTIVE_STORM = "tormenta_convectiva_severa"
    HEAT_WAVE = "ola_de_calor"
    COLD_WAVE = "ola_de_frio"
    FROST = "helada"
    EXTREME_HEAT = "calor_extremo"


class RiskLevel(str, Enum):
    """Niveles de riesgo."""
    
    LOW = "bajo"
    MODERATE = "moderado"
    HIGH = "alto"
    EXTREME = "extremo"


class DetectedPattern(BaseModel):
    """Patrón meteorológico detectado."""
    
    pattern_type: PatternType
    risk_level: RiskLevel
    confidence: float = Field(ge=0, le=1)
    
    # Descripción
    title: str
    description: str
    
    # Datos que lo activaron
    trigger_values: dict[str, float] = Field(default_factory=dict)
    thresholds_exceeded: list[str] = Field(default_factory=list)
    
    # Recomendaciones
    recommendations: list[str] = Field(default_factory=list)
    
    # Metadata
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    
    model_config = ConfigDict(use_enum_values=True)


class PatternDetector:
    """
    Detector de Patrones Meteorológicos.
    
    Detecta patrones basados en umbrales configurables:
    - Tormentas Convectivas Severas
    - Olas de Calor/Frío
    - Heladas
    """
    
    # Umbrales para detección (configurables)
    THRESHOLDS = {
        # Tormentas Convectivas
        "cape_moderate": 1000,      # J/kg - Convección moderada
        "cape_strong": 2000,        # J/kg - Convección fuerte
        "cape_extreme": 3000,       # J/kg - Convección extrema
        "wind_gust_severe": 25,     # m/s - Ráfagas severas (~90 km/h)
        "precip_intense": 30,       # mm/h - Precipitación intensa
        
        # Temperatura
        "heat_wave_day": 35,        # °C - Umbral ola de calor (día)
        "heat_wave_night": 22,      # °C - Umbral ola de calor (noche)
        "extreme_heat": 40,         # °C - Calor extremo
        "cold_wave": 5,             # °C - Umbral ola de frío
        "frost": 0,                 # °C - Helada
        "severe_frost": -5,         # °C - Helada severa
        
        # Días consecutivos para olas
        "wave_min_days": 3,
    }
    
    def detect_patterns(
        self,
        forecasts: list[UnifiedForecast],
        cape_values: Optional[list[float]] = None
    ) -> list[DetectedPattern]:
        """
        Detecta patrones en una serie de pronósticos.
        
        Args:
            forecasts: Lista de pronósticos fusionados
            cape_values: Valores CAPE opcionales (si disponibles)
            
        Returns:
            Lista de patrones detectados
        """
        if not forecasts:
            return []
        
        patterns = []
        
        # Detectar tormentas convectivas
        storm_pattern = self._detect_convective_storm(forecasts, cape_values)
        if storm_pattern:
            patterns.append(storm_pattern)
        
        # Detectar ola de calor
        heat_pattern = self._detect_heat_wave(forecasts)
        if heat_pattern:
            patterns.append(heat_pattern)
        
        # Detectar ola de frío
        cold_pattern = self._detect_cold_wave(forecasts)
        if cold_pattern:
            patterns.append(cold_pattern)
        
        # Detectar heladas
        frost_pattern = self._detect_frost(forecasts)
        if frost_pattern:
            patterns.append(frost_pattern)
        
        # Detectar calor extremo (evento puntual)
        extreme_heat = self._detect_extreme_heat(forecasts)
        if extreme_heat:
            patterns.append(extreme_heat)
        
        logger.info(f"Detectados {len(patterns)} patrones meteorológicos")
        return patterns
    
    def detect_from_current(
        self,
        current: UnifiedForecast,
        cape: Optional[float] = None
    ) -> list[DetectedPattern]:
        """
        Detecta patrones en condiciones actuales.
        
        Args:
            current: Pronóstico actual fusionado
            cape: Valor CAPE opcional
            
        Returns:
            Lista de patrones detectados
        """
        patterns = []
        
        # Tormenta convectiva (si hay CAPE)
        if cape is not None and cape >= self.THRESHOLDS["cape_moderate"]:
            pattern = self._create_storm_pattern(cape, current)
            if pattern:
                patterns.append(pattern)
        
        # Calor extremo
        if current.temperature_celsius and current.temperature_celsius >= self.THRESHOLDS["extreme_heat"]:
            patterns.append(self._create_extreme_heat_pattern(current))
        
        # Helada
        if current.temperature_celsius is not None and current.temperature_celsius <= self.THRESHOLDS["frost"]:
            patterns.append(self._create_frost_pattern_single(current))
        
        return patterns
    
    def _detect_convective_storm(
        self,
        forecasts: list[UnifiedForecast],
        cape_values: Optional[list[float]]
    ) -> Optional[DetectedPattern]:
        """Detecta potencial de tormentas convectivas severas."""
        
        if not cape_values:
            # Sin CAPE, usar proxy: precipitación intensa + viento fuerte
            return self._detect_storm_by_proxy(forecasts)
        
        max_cape = max(cape_values)
        if max_cape < self.THRESHOLDS["cape_moderate"]:
            return None
        
        # Determinar nivel de riesgo
        if max_cape >= self.THRESHOLDS["cape_extreme"]:
            risk = RiskLevel.EXTREME
            confidence = 0.9
        elif max_cape >= self.THRESHOLDS["cape_strong"]:
            risk = RiskLevel.HIGH
            confidence = 0.8
        else:
            risk = RiskLevel.MODERATE
            confidence = 0.7
        
        recommendations = self._get_storm_recommendations(risk)
        
        return DetectedPattern(
            pattern_type=PatternType.SEVERE_CONVECTIVE_STORM,
            risk_level=risk,
            confidence=confidence,
            title="Tormenta Convectiva Severa",
            description=f"Ambiente favorable para tormentas severas. CAPE: {max_cape:.0f} J/kg",
            trigger_values={"cape_max": max_cape},
            thresholds_exceeded=["CAPE > 1000 J/kg"],
            recommendations=recommendations
        )
    
    def _detect_storm_by_proxy(
        self,
        forecasts: list[UnifiedForecast]
    ) -> Optional[DetectedPattern]:
        """Detecta tormentas usando precipitación y viento como proxy."""
        
        max_precip = max(
            (f.precipitation_mm or 0 for f in forecasts),
            default=0
        )
        max_wind = max(
            (f.wind_speed_ms or 0 for f in forecasts),
            default=0
        )
        
        # Necesita precipitación significativa Y viento fuerte
        if max_precip < 15 or max_wind < 15:
            return None
        
        # Calcular riesgo basado en intensidad
        risk_score = (max_precip / 50) + (max_wind / 30)
        
        if risk_score >= 1.5:
            risk = RiskLevel.HIGH
            confidence = 0.6
        elif risk_score >= 1.0:
            risk = RiskLevel.MODERATE
            confidence = 0.5
        else:
            return None
        
        return DetectedPattern(
            pattern_type=PatternType.SEVERE_CONVECTIVE_STORM,
            risk_level=risk,
            confidence=confidence,
            title="Posible Tormenta Severa",
            description=f"Precipitación intensa ({max_precip:.1f}mm) con vientos fuertes ({max_wind:.1f}m/s)",
            trigger_values={"precipitation_mm": max_precip, "wind_speed_ms": max_wind},
            thresholds_exceeded=["Precipitación > 15mm", "Viento > 15 m/s"],
            recommendations=self._get_storm_recommendations(risk)
        )
    
    def _detect_heat_wave(
        self,
        forecasts: list[UnifiedForecast]
    ) -> Optional[DetectedPattern]:
        """Detecta ola de calor (3+ días con temp > umbral)."""
        
        temps = [f.temperature_celsius for f in forecasts if f.temperature_celsius is not None]
        if not temps:
            return None
        
        # Contar días con temperatura alta
        # Simplificación: cada 24h de pronóstico = 1 día
        high_temp_hours = sum(1 for t in temps if t >= self.THRESHOLDS["heat_wave_day"])
        high_temp_days = high_temp_hours / 24
        
        if high_temp_days < 2:  # Mínimo 2 días para alertar
            return None
        
        max_temp = max(temps)
        avg_temp = sum(temps) / len(temps)
        
        # Determinar riesgo
        if max_temp >= self.THRESHOLDS["extreme_heat"] or high_temp_days >= 5:
            risk = RiskLevel.EXTREME
            confidence = 0.85
        elif high_temp_days >= 3:
            risk = RiskLevel.HIGH
            confidence = 0.8
        else:
            risk = RiskLevel.MODERATE
            confidence = 0.7
        
        return DetectedPattern(
            pattern_type=PatternType.HEAT_WAVE,
            risk_level=risk,
            confidence=confidence,
            title="Ola de Calor",
            description=f"Temperaturas elevadas sostenidas. Máxima: {max_temp:.1f}°C, Promedio: {avg_temp:.1f}°C",
            trigger_values={
                "max_temperature": max_temp,
                "avg_temperature": avg_temp,
                "days_above_threshold": round(high_temp_days, 1)
            },
            thresholds_exceeded=[f"Temperatura > {self.THRESHOLDS['heat_wave_day']}°C por {high_temp_days:.1f} días"],
            recommendations=self._get_heat_recommendations(risk)
        )
    
    def _detect_cold_wave(
        self,
        forecasts: list[UnifiedForecast]
    ) -> Optional[DetectedPattern]:
        """Detecta ola de frío (3+ días con temp < umbral)."""
        
        temps = [f.temperature_celsius for f in forecasts if f.temperature_celsius is not None]
        if not temps:
            return None
        
        low_temp_hours = sum(1 for t in temps if t <= self.THRESHOLDS["cold_wave"])
        low_temp_days = low_temp_hours / 24
        
        if low_temp_days < 2:
            return None
        
        min_temp = min(temps)
        avg_temp = sum(temps) / len(temps)
        
        if min_temp <= self.THRESHOLDS["severe_frost"] or low_temp_days >= 5:
            risk = RiskLevel.EXTREME
            confidence = 0.85
        elif low_temp_days >= 3:
            risk = RiskLevel.HIGH
            confidence = 0.8
        else:
            risk = RiskLevel.MODERATE
            confidence = 0.7
        
        return DetectedPattern(
            pattern_type=PatternType.COLD_WAVE,
            risk_level=risk,
            confidence=confidence,
            title="Ola de Frío",
            description=f"Temperaturas bajas sostenidas. Mínima: {min_temp:.1f}°C, Promedio: {avg_temp:.1f}°C",
            trigger_values={
                "min_temperature": min_temp,
                "avg_temperature": avg_temp,
                "days_below_threshold": round(low_temp_days, 1)
            },
            thresholds_exceeded=[f"Temperatura < {self.THRESHOLDS['cold_wave']}°C por {low_temp_days:.1f} días"],
            recommendations=self._get_cold_recommendations(risk)
        )
    
    def _detect_frost(
        self,
        forecasts: list[UnifiedForecast]
    ) -> Optional[DetectedPattern]:
        """Detecta heladas."""
        
        temps = [f.temperature_celsius for f in forecasts if f.temperature_celsius is not None]
        if not temps:
            return None
        
        min_temp = min(temps)
        
        if min_temp > self.THRESHOLDS["frost"]:
            return None
        
        frost_hours = sum(1 for t in temps if t <= self.THRESHOLDS["frost"])
        
        if min_temp <= self.THRESHOLDS["severe_frost"]:
            risk = RiskLevel.EXTREME
            title = "Helada Severa"
            confidence = 0.9
        elif min_temp <= -2:
            risk = RiskLevel.HIGH
            title = "Helada Fuerte"
            confidence = 0.85
        else:
            risk = RiskLevel.MODERATE
            title = "Helada"
            confidence = 0.8
        
        return DetectedPattern(
            pattern_type=PatternType.FROST,
            risk_level=risk,
            confidence=confidence,
            title=title,
            description=f"Temperatura mínima: {min_temp:.1f}°C. Horas bajo 0°C: {frost_hours}",
            trigger_values={
                "min_temperature": min_temp,
                "frost_hours": frost_hours
            },
            thresholds_exceeded=[f"Temperatura < {self.THRESHOLDS['frost']}°C"],
            recommendations=self._get_frost_recommendations(risk)
        )
    
    def _detect_extreme_heat(
        self,
        forecasts: list[UnifiedForecast]
    ) -> Optional[DetectedPattern]:
        """Detecta evento de calor extremo puntual."""
        
        temps = [f.temperature_celsius for f in forecasts if f.temperature_celsius is not None]
        if not temps:
            return None
        
        max_temp = max(temps)
        
        if max_temp < self.THRESHOLDS["extreme_heat"]:
            return None
        
        return DetectedPattern(
            pattern_type=PatternType.EXTREME_HEAT,
            risk_level=RiskLevel.EXTREME,
            confidence=0.9,
            title="Calor Extremo",
            description=f"Temperatura máxima: {max_temp:.1f}°C - Condiciones peligrosas",
            trigger_values={"max_temperature": max_temp},
            thresholds_exceeded=[f"Temperatura > {self.THRESHOLDS['extreme_heat']}°C"],
            recommendations=self._get_extreme_heat_recommendations()
        )
    
    def _create_storm_pattern(
        self,
        cape: float,
        current: UnifiedForecast
    ) -> Optional[DetectedPattern]:
        """Crea patrón de tormenta desde CAPE actual."""
        
        if cape >= self.THRESHOLDS["cape_extreme"]:
            risk = RiskLevel.EXTREME
        elif cape >= self.THRESHOLDS["cape_strong"]:
            risk = RiskLevel.HIGH
        else:
            risk = RiskLevel.MODERATE
        
        return DetectedPattern(
            pattern_type=PatternType.SEVERE_CONVECTIVE_STORM,
            risk_level=risk,
            confidence=0.8,
            title="Ambiente Tormentoso",
            description=f"CAPE actual: {cape:.0f} J/kg - Potencial convectivo {'extremo' if risk == RiskLevel.EXTREME else 'alto' if risk == RiskLevel.HIGH else 'moderado'}",
            trigger_values={"cape": cape},
            thresholds_exceeded=[f"CAPE > {self.THRESHOLDS['cape_moderate']} J/kg"],
            recommendations=self._get_storm_recommendations(risk)
        )
    
    def _create_extreme_heat_pattern(
        self,
        current: UnifiedForecast
    ) -> DetectedPattern:
        """Crea patrón de calor extremo."""
        return DetectedPattern(
            pattern_type=PatternType.EXTREME_HEAT,
            risk_level=RiskLevel.EXTREME,
            confidence=0.95,
            title="Calor Extremo Actual",
            description=f"Temperatura actual: {current.temperature_celsius:.1f}°C",
            trigger_values={"temperature": current.temperature_celsius},
            thresholds_exceeded=[f"Temperatura > {self.THRESHOLDS['extreme_heat']}°C"],
            recommendations=self._get_extreme_heat_recommendations()
        )
    
    def _create_frost_pattern_single(
        self,
        current: UnifiedForecast
    ) -> DetectedPattern:
        """Crea patrón de helada actual."""
        temp = current.temperature_celsius
        
        if temp <= self.THRESHOLDS["severe_frost"]:
            risk = RiskLevel.EXTREME
            title = "Helada Severa Actual"
        elif temp <= -2:
            risk = RiskLevel.HIGH
            title = "Helada Actual"
        else:
            risk = RiskLevel.MODERATE
            title = "Temperatura Bajo Cero"
        
        return DetectedPattern(
            pattern_type=PatternType.FROST,
            risk_level=risk,
            confidence=0.95,
            title=title,
            description=f"Temperatura actual: {temp:.1f}°C",
            trigger_values={"temperature": temp},
            thresholds_exceeded=["Temperatura ≤ 0°C"],
            recommendations=self._get_frost_recommendations(risk)
        )
    
    # === Recomendaciones por tipo de patrón ===
    
    def _get_storm_recommendations(self, risk: RiskLevel) -> list[str]:
        """Recomendaciones para tormentas."""
        base = [
            "Monitorear radar meteorológico",
            "Evitar actividades al aire libre",
            "Asegurar objetos que puedan volar",
        ]
        if risk in [RiskLevel.HIGH, RiskLevel.EXTREME]:
            base.extend([
                "Buscar refugio en estructura sólida",
                "Alejarse de árboles y postes",
                "No cruzar zonas inundadas",
                "Desconectar equipos eléctricos sensibles",
            ])
        if risk == RiskLevel.EXTREME:
            base.extend([
                "Posible granizo grande - proteger vehículos",
                "Riesgo de tornados - identificar refugio más cercano",
            ])
        return base
    
    def _get_heat_recommendations(self, risk: RiskLevel) -> list[str]:
        """Recomendaciones para ola de calor."""
        base = [
            "Hidratarse frecuentemente",
            "Evitar exposición solar entre 10-16h",
            "Usar ropa clara y liviana",
        ]
        if risk in [RiskLevel.HIGH, RiskLevel.EXTREME]:
            base.extend([
                "Permanecer en lugares frescos o con AC",
                "No dejar personas/mascotas en vehículos",
                "Reducir actividad física intensa",
                "Atención a adultos mayores y niños",
            ])
        return base
    
    def _get_cold_recommendations(self, risk: RiskLevel) -> list[str]:
        """Recomendaciones para ola de frío."""
        base = [
            "Abrigarse en capas",
            "Mantener calefacción adecuada",
            "Proteger tuberías de agua",
        ]
        if risk in [RiskLevel.HIGH, RiskLevel.EXTREME]:
            base.extend([
                "Evitar exposición prolongada al frío",
                "Atención a personas en situación de calle",
                "Verificar calefacción a gas (ventilación)",
                "Proteger mascotas del frío extremo",
            ])
        return base
    
    def _get_frost_recommendations(self, risk: RiskLevel) -> list[str]:
        """Recomendaciones para heladas."""
        base = [
            "Proteger cultivos sensibles",
            "Cubrir plantas con tela antihelada",
            "Drenar mangueras y sistemas de riego",
        ]
        if risk in [RiskLevel.HIGH, RiskLevel.EXTREME]:
            base.extend([
                "Riesgo de hielo en rutas - precaución al conducir",
                "Proteger cañerías exteriores",
                "Cosecha de emergencia si es posible",
            ])
        return base
    
    def _get_extreme_heat_recommendations(self) -> list[str]:
        """Recomendaciones para calor extremo."""
        return [
            "ALERTA: Condiciones peligrosas para la salud",
            "Permanecer en interiores con AC",
            "Hidratación constante (agua, no alcohol)",
            "No realizar actividad física",
            "Atención inmediata a síntomas de golpe de calor",
            "No dejar personas/mascotas en vehículos bajo ninguna circunstancia",
            "Contactar servicios de emergencia ante síntomas graves",
        ]

