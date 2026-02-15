"""Esquema de entrada para el motor de clasificación de amenazas (M2).

Datos actuales de modelo/radar; campos opcionales para futura integración GOES/SINARAME.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ThreatClassificationInput(BaseModel):
    """
    Entrada al clasificador de amenazas.

    - Campos actuales (modelo/fusión): temperatura, precipitación, nubosidad, weather_code.
    - Opcionales para radar/GOES: reflectivity_dbz, freezing_level_m (altura del 0°C).
    """

    temperature_celsius: Optional[float] = Field(default=None, ge=-60, le=60)
    precipitation_mm: Optional[float] = Field(default=None, ge=0)
    cloud_cover_pct: Optional[float] = Field(default=None, ge=0, le=100)
    weather_code: Optional[int] = Field(default=None, ge=0, le=99)
    reflectivity_dbz: Optional[float] = Field(default=None, ge=0, le=80)
    freezing_level_m: Optional[float] = Field(default=None, ge=0)
