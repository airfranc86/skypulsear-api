"""
Risk Profiles Configuration

Defines all user profiles and their specific risk sensitivities for SkyPulse.
"""

from enum import Enum
from typing import Dict, Any
from pydantic import BaseModel, Field


class UserProfile(str, Enum):
    """Perfiles de usuario soportados por SkyPulse."""

    PILOT = "piloto"
    TRUCKER = "camionero"
    AGRICULTURE = "agricultor"
    CONSTRUCTION = "construccion"
    TOURISM = "turismo"
    EVENT_ORGANIZER = "organizador_eventos"
    GENERAL = "general"


class RiskCategory(str, Enum):
    """Categorías de riesgo para SkyPulse."""

    VERY_LOW = "muy_bajo"
    LOW = "bajo"
    MODERATE = "moderado"
    HIGH = "alto"
    VERY_HIGH = "muy_alto"
    EXTREME = "extremo"


class RiskProfileConfig(BaseModel):
    """Configuración de perfil de riesgo."""

    profile: UserProfile
    profile_name: str
    description: str

    # Sensibilidades de factores de riesgo (0-100)
    temperature_sensitivity: int = Field(default=50, ge=0, le=100)
    wind_sensitivity: int = Field(default=60, ge=0, le=100)
    precipitation_sensitivity: int = Field(default=70, ge=0, le=100)
    storm_sensitivity: int = Field(default=80, ge=0, le=100)
    pattern_sensitivity: int = Field(default=50, ge=0, le=100)

    # Umbrales de riesgo (0-100)
    very_low_threshold: int = Field(default=20, ge=0, le=100)
    low_threshold: int = Field(default=40, ge=0, le=100)
    moderate_threshold: int = Field(default=60, ge=0, le=100)
    high_threshold: int = Field(default=80, ge=0, le=100)
    very_high_threshold: int = Field(default=90, ge=0, le=100)


class ProfileConfigurations:
    """Configuraciones predefinidas para todos los perfiles."""

    @staticmethod
    def get_profile(profile: UserProfile) -> RiskProfileConfig:
        """Obtener configuración de perfil específica."""
        profiles = {
            UserProfile.PILOT: RiskProfileConfig(
                profile=UserProfile.PILOT,
                profile_name="Piloto de Aviación",
                description="Sensibilidad alta a vientos fuertes y tormentas",
                temperature_sensitivity=30,
                wind_sensitivity=90,
                precipitation_sensitivity=60,
                storm_sensitivity=95,
                pattern_sensitivity=70,
                very_low_threshold=10,
                low_threshold=25,
                moderate_threshold=50,
                high_threshold=75,
                very_high_threshold=90,
            ),
            UserProfile.TRUCKER: RiskProfileConfig(
                profile=UserProfile.TRUCKER,
                profile_name="Camionero",
                description="Enfoque en visibilidad y condiciones de camino",
                temperature_sensitivity=40,
                wind_sensitivity=70,
                precipitation_sensitivity=80,
                storm_sensitivity=60,
                pattern_sensitivity=60,
                very_low_threshold=15,
                low_threshold=35,
                moderate_threshold=55,
                high_threshold=75,
                very_high_threshold=85,
            ),
            UserProfile.AGRICULTURE: RiskProfileConfig(
                profile=UserProfile.AGRICULTURE,
                profile_name="Agricultura",
                description="Enfoque en lluvia, temperatura y heladas",
                temperature_sensitivity=70,
                wind_sensitivity=40,
                precipitation_sensitivity=90,
                storm_sensitivity=70,
                pattern_sensitivity=50,
                very_low_threshold=20,
                low_threshold=40,
                moderate_threshold=60,
                high_threshold=75,
                very_high_threshold=85,
            ),
            UserProfile.CONSTRUCTION: RiskProfileConfig(
                profile=UserProfile.CONSTRUCTION,
                profile_name="Construcción",
                description="Enfoque en vientos y condiciones climáticas extremas",
                temperature_sensitivity=30,
                wind_sensitivity=80,
                precipitation_sensitivity=70,
                storm_sensitivity=85,
                pattern_sensitivity=60,
                very_low_threshold=20,
                low_threshold=35,
                moderate_threshold=50,
                high_threshold=70,
                very_high_threshold=85,
            ),
            UserProfile.TOURISM: RiskProfileConfig(
                profile=UserProfile.TOURISM,
                profile_name="Turismo",
                description="Enfoque en condiciones agradables y seguridad",
                temperature_sensitivity=50,
                wind_sensitivity=50,
                precipitation_sensitivity=60,
                storm_sensitivity=50,
                pattern_sensitivity=40,
                very_low_threshold=25,
                low_threshold=40,
                moderate_threshold=60,
                high_threshold=75,
                very_high_threshold=85,
            ),
            UserProfile.EVENT_ORGANIZER: RiskProfileConfig(
                profile=UserProfile.EVENT_ORGANIZER,
                profile_name="Organizador de Eventos",
                description="Enfoque en patrones meteorológicos para planificación",
                temperature_sensitivity=40,
                wind_sensitivity=60,
                precipitation_sensitivity=70,
                storm_sensitivity=80,
                pattern_sensitivity=90,
                very_low_threshold=15,
                low_threshold=30,
                moderate_threshold=50,
                high_threshold=70,
                very_high_threshold=85,
            ),
            UserProfile.GENERAL: RiskProfileConfig(
                profile=UserProfile.GENERAL,
                profile_name="General",
                description="Configuración equilibrada para público general",
                temperature_sensitivity=50,
                wind_sensitivity=50,
                precipitation_sensitivity=50,
                storm_sensitivity=50,
                pattern_sensitivity=50,
                very_low_threshold=20,
                low_threshold=40,
                moderate_threshold=60,
                high_threshold=75,
                very_high_threshold=85,
            ),
        }
        return profiles.get(
            profile, ProfileConfigurations.get_profile(UserProfile.GENERAL)
        )


class WeatherConditionThresholds:
    """Umbrales de condiciones meteorológicas para cálculo de riesgo."""

    # Temperatura (C)
    EXTREME_HEAT: float = 40.0
    VERY_HOT: float = 35.0
    HOT: float = 30.0
    WARM: float = 25.0
    MODERATE: float = 20.0
    COOL: float = 15.0
    COLD: float = 10.0
    FREEZING: float = 5.0
    EXTREME_COLD: float = 0.0

    # Viento (km/h)
    CALM: float = 0.0
    LIGHT_BREEZE: float = 10.0
    MODERATE_WIND: float = 20.0
    STRONG_WIND: float = 30.0
    GALE_FORCE: float = 40.0
    EXTREME_WIND: float = 50.0

    # Precipitación (mm/h)
    NO_RAIN: float = 0.0
    LIGHT_RAIN: float = 2.5
    MODERATE_RAIN: float = 5.0
    HEAVY_RAIN: float = 10.0
    EXTREME_RAIN: float = 20.0

    @classmethod
    def get_temperature_category(cls, temp_c: float) -> RiskCategory:
        """Categorizar temperatura."""
        if temp_c >= cls.EXTREME_HEAT:
            return RiskCategory.EXTREME
        elif temp_c >= cls.VERY_HOT:
            return RiskCategory.VERY_HIGH
        elif temp_c >= cls.HOT:
            return RiskCategory.HIGH
        elif temp_c >= cls.WARM:
            return RiskCategory.MODERATE
        elif temp_c >= cls.MODERATE:
            return RiskCategory.LOW
        elif temp_c >= cls.COOL:
            return RiskCategory.VERY_LOW
        else:
            return RiskCategory.VERY_LOW

    @classmethod
    def get_wind_category(cls, wind_speed: float) -> RiskCategory:
        """Categorizar velocidad de viento."""
        if wind_speed >= cls.EXTREME_WIND:
            return RiskCategory.EXTREME
        elif wind_speed >= cls.GALE_FORCE:
            return RiskCategory.VERY_HIGH
        elif wind_speed >= cls.STRONG_WIND:
            return RiskCategory.HIGH
        elif wind_speed >= cls.MODERATE_WIND:
            return RiskCategory.MODERATE
        elif wind_speed >= cls.LIGHT_BREEZE:
            return RiskCategory.LOW
        else:
            return RiskCategory.VERY_LOW

    @classmethod
    def get_precipitation_category(cls, precip: float) -> RiskCategory:
        """Categorizar precipitación."""
        if precip >= cls.EXTREME_RAIN:
            return RiskCategory.EXTREME
        elif precip >= cls.HEAVY_RAIN:
            return RiskCategory.VERY_HIGH
        elif precip >= cls.MODERATE_RAIN:
            return RiskCategory.HIGH
        elif precip >= cls.LIGHT_RAIN:
            return RiskCategory.MODERATE
        else:
            return RiskCategory.VERY_LOW
