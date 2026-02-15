"""Lógica física (dBZ, 0°C) y heurística Shelf/Wall/proxy granizo (M2.2).

Funciones puras: entrada → lista de ClassifiedThreat.
Sin radar: se usan proxies (precipitación fuerte + temperatura baja → posible granizo).
"""

from __future__ import annotations

from typing import List

from app.models.threat_classification import ClassifiedThreat, ThreatType
from app.services.threat_classification.inputs import ThreatClassificationInput

# Umbrales físicos (radar cuando exista)
DBZ_HAIL_PROXY_HIGH = 55.0
DBZ_HAIL_PROXY_MODERATE = 50.0
DBZ_SEVERE_CONVECTION = 45.0

# Proxies con datos de modelo (sin radar)
PRECIP_MM_SEVERE = 8.0
PRECIP_MM_CONVECTION = 3.0
CLOUD_COVER_CONVECTION_PCT = 70.0
TEMP_C_HAIL_PROXY_MAX = 5.0  # Por debajo de esto + precip fuerte → proxy granizo
TEMP_C_FREEZING = 0.0


def classify_threats(data: ThreatClassificationInput) -> List[ClassifiedThreat]:
    """
    Clasifica amenazas a partir de datos actuales (modelo/radar).

    Orden: (1) proxy granizo (dBZ bajo 0°C o proxy precip+T), (2) convección severa,
    (3) Shelf/Wall solo si en el futuro hay estructura de radar.
    """
    out: List[ClassifiedThreat] = []

    # Hail proxy con radar: dBZ > 50–55 bajo 0°C
    if (
        data.reflectivity_dbz is not None
        and data.freezing_level_m is not None
        and data.reflectivity_dbz >= DBZ_HAIL_PROXY_MODERATE
    ):
        level = 3 if data.reflectivity_dbz >= DBZ_HAIL_PROXY_HIGH else 2
        out.append(
            ClassifiedThreat(
                threat_type=ThreatType.HAIL_PROXY,
                level=level,
                label="Posible granizo (dBZ bajo 0°C)",
                criterion_used=f"dBZ>={data.reflectivity_dbz:.0f} bajo nivel 0°C",
                raw_hint={
                    "reflectivity_dbz": data.reflectivity_dbz,
                    "freezing_level_m": data.freezing_level_m,
                },
            )
        )
        return out

    # Hail proxy sin radar: precipitación fuerte y temperatura baja
    temp = data.temperature_celsius
    precip = data.precipitation_mm or 0.0
    cloud = data.cloud_cover_pct or 0.0

    if (
        temp is not None
        and temp <= TEMP_C_HAIL_PROXY_MAX
        and precip >= PRECIP_MM_SEVERE
    ):
        level = 2 if temp <= TEMP_C_FREEZING else 1
        out.append(
            ClassifiedThreat(
                threat_type=ThreatType.HAIL_PROXY,
                level=level,
                label="Posible granizo (proxy precip + T baja)",
                criterion_used=f"precip={precip:.1f}mm, T={temp:.1f}°C",
                raw_hint={"precipitation_mm": precip, "temperature_celsius": temp},
            )
        )
        return out

    # Convección severa: precip + nubosidad alta (sin estructura Shelf/Wall por ahora)
    if precip >= PRECIP_MM_SEVERE and cloud >= CLOUD_COVER_CONVECTION_PCT:
        out.append(
            ClassifiedThreat(
                threat_type=ThreatType.SEVERE_CONVECTION,
                level=2,
                label="Convección severa",
                criterion_used=f"precip={precip:.1f}mm, nubosidad={cloud:.0f}%",
                raw_hint={"precipitation_mm": precip, "cloud_cover_pct": cloud},
            )
        )
        return out

    if precip >= PRECIP_MM_CONVECTION and cloud >= CLOUD_COVER_CONVECTION_PCT:
        out.append(
            ClassifiedThreat(
                threat_type=ThreatType.SEVERE_CONVECTION,
                level=1,
                label="Convección moderada",
                criterion_used=f"precip={precip:.1f}mm, nubosidad={cloud:.0f}%",
                raw_hint={"precipitation_mm": precip, "cloud_cover_pct": cloud},
            )
        )
        return out

    # Código WMO de tormenta/granizo (95, 96, 99, 77)
    wmo = data.weather_code
    if wmo is not None and wmo in (77, 95, 96, 99):
        out.append(
            ClassifiedThreat(
                threat_type=ThreatType.SEVERE_CONVECTION,
                level=2 if wmo in (96, 99) else 1,
                label="Tormenta (código WMO)",
                criterion_used=f"weather_code={wmo}",
                raw_hint={"weather_code": wmo},
            )
        )
        return out

    return out
