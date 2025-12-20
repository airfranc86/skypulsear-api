"""Schemas normalizados para el Motor de Fusión Unificado."""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeatherSource(str, Enum):
    """Fuentes de datos meteorológicos soportadas."""

    METEOSOURCE = "meteosource"
    METEOSOURCE_WRF = "meteosource_wrf"
    WINDY_ECMWF = "windy_ecmwf"
    WINDY_GFS = "windy_gfs"
    WINDY_ICON = "windy_icon"
    WRF_SMN = "wrf_smn"
    LOCAL_STATIONS = "local_stations"
    FUSED = "fused"  # Resultado de fusión


class ConfidenceLevel(str, Enum):
    """Niveles de confianza del pronóstico."""

    VERY_HIGH = "very_high"  # > 0.9
    HIGH = "high"  # 0.7 - 0.9
    MEDIUM = "medium"  # 0.5 - 0.7
    LOW = "low"  # 0.3 - 0.5
    VERY_LOW = "very_low"  # < 0.3


class NormalizedWeatherData(BaseModel):
    """Datos meteorológicos normalizados de cualquier fuente."""

    # Identificación
    source: WeatherSource
    timestamp: datetime
    forecast_hour: int = Field(
        ge=0, le=240, description="Hora de pronóstico (0=actual)"
    )

    # Ubicación
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    # Variables meteorológicas (unidades estandarizadas)
    temperature_celsius: Optional[float] = Field(default=None, ge=-100, le=60)
    wind_speed_ms: Optional[float] = Field(default=None, ge=0, le=150)
    wind_direction_deg: Optional[float] = Field(default=None, ge=0, le=360)
    precipitation_mm: Optional[float] = Field(default=None, ge=0)
    cloud_cover_pct: Optional[float] = Field(default=None, ge=0, le=100)
    humidity_pct: Optional[float] = Field(default=None, ge=0, le=100)
    pressure_hpa: Optional[float] = Field(default=None, ge=800, le=1100)

    # Metadatos
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_data: Optional[dict] = Field(default=None, exclude=True)

    @field_validator("wind_direction_deg")
    @classmethod
    def normalize_wind_direction(cls, v: Optional[float]) -> Optional[float]:
        """Normaliza dirección del viento a 0-360."""
        if v is None:
            return None
        return v % 360

    model_config = ConfigDict(use_enum_values=True)


class SourceContribution(BaseModel):
    """Contribución de una fuente al valor fusionado."""

    source: WeatherSource
    value: float
    weight: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)


class FusionWeights(BaseModel):
    """Pesos de fusión por variable y horizonte temporal."""

    # Pesos para temperatura (0-72h)
    temperature_short: dict[str, float] = Field(
        default={
            "wrf_smn": 0.35,
            "windy_ecmwf": 0.30,
            "windy_gfs": 0.20,
            "meteosource": 0.15,
        }
    )

    # Pesos para temperatura (3-10 días)
    temperature_long: dict[str, float] = Field(
        default={
            "windy_ecmwf": 0.40,
            "windy_gfs": 0.30,
            "meteosource": 0.30,
        }
    )

    # Pesos para viento (0-72h)
    wind_short: dict[str, float] = Field(
        default={
            "wrf_smn": 0.40,
            "windy_ecmwf": 0.30,
            "windy_gfs": 0.15,
            "meteosource": 0.15,
        }
    )

    # Pesos para viento (3-10 días)
    wind_long: dict[str, float] = Field(
        default={
            "windy_ecmwf": 0.45,
            "windy_gfs": 0.30,
            "meteosource": 0.25,
        }
    )

    # Pesos para precipitación (0-72h)
    precipitation_short: dict[str, float] = Field(
        default={
            "wrf_smn": 0.45,
            "windy_ecmwf": 0.30,
            "windy_gfs": 0.15,
            "meteosource": 0.10,
        }
    )

    # Pesos para precipitación (3-10 días)
    precipitation_long: dict[str, float] = Field(
        default={
            "windy_ecmwf": 0.45,
            "windy_gfs": 0.35,
            "meteosource": 0.20,
        }
    )

    def get_weights(self, variable: str, forecast_hour: int) -> dict[str, float]:
        """Obtiene pesos según variable y horizonte temporal."""
        is_short_term = forecast_hour <= 72

        weight_map = {
            ("temperature", True): self.temperature_short,
            ("temperature", False): self.temperature_long,
            ("wind", True): self.wind_short,
            ("wind", False): self.wind_long,
            ("precipitation", True): self.precipitation_short,
            ("precipitation", False): self.precipitation_long,
        }

        return weight_map.get((variable, is_short_term), self.temperature_short)


class InconsistencyReport(BaseModel):
    """Reporte de inconsistencias entre fuentes."""

    variable: str
    timestamp: datetime
    forecast_hour: int

    # Valores por fuente
    source_values: dict[str, float]

    # Estadísticas
    mean_value: float
    std_deviation: float
    max_deviation: float
    coefficient_of_variation: float = Field(ge=0)

    # Fuentes problemáticas
    outlier_sources: list[str] = Field(default_factory=list)

    # Severidad (0-1, donde 1 es máxima inconsistencia)
    severity: float = Field(ge=0, le=1)

    @property
    def is_significant(self) -> bool:
        """Determina si la inconsistencia es significativa."""
        return self.severity > 0.3


class UnifiedForecast(BaseModel):
    """Pronóstico fusionado de múltiples fuentes."""

    # Identificación
    timestamp: datetime
    forecast_hour: int = Field(ge=0, le=240)
    latitude: float
    longitude: float

    # Valores fusionados
    temperature_celsius: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    humidity_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None

    # Confianza por variable (0-1)
    temperature_confidence: float = Field(default=0.5, ge=0, le=1)
    wind_confidence: float = Field(default=0.5, ge=0, le=1)
    precipitation_confidence: float = Field(default=0.5, ge=0, le=1)

    # Confianza global
    overall_confidence: float = Field(default=0.5, ge=0, le=1)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Contribuciones por fuente
    temperature_contributions: list[SourceContribution] = Field(default_factory=list)
    wind_contributions: list[SourceContribution] = Field(default_factory=list)
    precipitation_contributions: list[SourceContribution] = Field(default_factory=list)

    # Fuentes utilizadas
    sources_used: list[WeatherSource] = Field(default_factory=list)
    sources_available: int = 0

    # Inconsistencias detectadas
    inconsistencies: list[InconsistencyReport] = Field(default_factory=list)
    has_significant_inconsistencies: bool = False

    # Metadatos
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fusion_method: str = "weighted_average"

    def get_confidence_level(self) -> ConfidenceLevel:
        """Calcula nivel de confianza basado en valor numérico."""
        if self.overall_confidence > 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.overall_confidence > 0.7:
            return ConfidenceLevel.HIGH
        elif self.overall_confidence > 0.5:
            return ConfidenceLevel.MEDIUM
        elif self.overall_confidence > 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    model_config = ConfigDict(use_enum_values=True)
