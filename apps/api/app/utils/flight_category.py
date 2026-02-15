"""Criterios OMM/OHMC para categoría de vuelo (M3 — UX seguridad aeronáutica).

Basado en visibilidad y techo (ceiling). Uso: badges VFR/MVFR/IFR/LIFR en dashboard.
Referencia: convención ICAO/OMM; visibilidad en km, techo en m.
"""

from typing import Optional

# Umbrales visibilidad (km) y techo (m) — criterios típicos OMM/OHMC
VIS_KM_VFR = 8.0
VIS_KM_MVFR = 5.0
VIS_KM_IFR = 1.5
CEILING_M_VFR = 457.0   # 1500 ft
CEILING_M_MVFR = 305.0  # 1000 ft
CEILING_M_IFR = 152.0   # 500 ft


def get_flight_category(
    visibility_km: float,
    ceiling_m: Optional[float] = None,
) -> str:
    """
    Deriva categoría de vuelo desde visibilidad y techo.

    - VFR:  vis >= 8 km y techo >= 1500 ft (457 m)
    - MVFR: vis 5–8 km o techo 1000–1500 ft (305–457 m)
    - IFR:  vis 1.5–5 km o techo 500–1000 ft (152–305 m)
    - LIFR: vis < 1.5 km o techo < 500 ft (152 m)

    Si ceiling_m es None, solo se usa visibilidad para clasificar.
    """
    if ceiling_m is not None and ceiling_m < CEILING_M_IFR:
        return "LIFR"
    if visibility_km < VIS_KM_IFR:
        return "LIFR"
    if ceiling_m is not None and ceiling_m < CEILING_M_MVFR:
        return "IFR"
    if visibility_km < VIS_KM_MVFR:
        return "IFR"
    if ceiling_m is not None and ceiling_m < CEILING_M_VFR:
        return "MVFR"
    if visibility_km < VIS_KM_VFR:
        return "MVFR"
    return "VFR"
