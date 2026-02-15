"""
Weather Router (Simplified for Phase 1)

Weather endpoints with basic protection for Phase 1 security implementation.
Conectado a UnifiedWeatherEngine para datos reales (Windy GFS/ECMWF + WRF-SMN).
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, Request

from app.api.dependencies import require_api_key
from app.services.unified_weather_engine import UnifiedWeatherEngine
from app.data.schemas.normalized_weather import UnifiedForecast
from app.utils.flight_category import get_flight_category

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["weather"])


def _deg_to_cardinal(deg: Optional[float]) -> str:
    """Convierte grados (0-360) a punto cardinal (N, NE, E, ...)."""
    if deg is None:
        return "N"
    directions = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
    ]
    idx = int((deg + 11.25) / 22.5) % 16
    return directions[idx]


def _conditions_from_forecast(f: UnifiedForecast) -> str:
    """Deriva descripción de condiciones a partir de cloud_cover y precipitación."""
    cloud = f.cloud_cover_pct or 0
    precip = f.precipitation_mm or 0
    if precip > 2:
        return "lluvia"
    if precip > 0:
        return "llovizna"
    if cloud >= 80:
        return "nublado"
    if cloud >= 50:
        return "parcialmente nublado"
    if cloud >= 20:
        return "parcialmente despejado"
    return "despejado"


# Etiquetas de fuente meteorológica para la UI (sin guiones bajos, no exponer IDs internos)
_METEO_SOURCE_DISPLAY: dict[str, str] = {
    "windy_ecmwf": "Windy ECMWF",
    "windy_gfs": "Windy GFS",
    "windy_icon": "Windy ICON",
    "wrf_smn": "WRF-SMN",
}


def _meteo_source_display_from_unified(f: UnifiedForecast) -> str:
    """Construye una única etiqueta para la UI a partir de sources_used (opción B, sin exponer lista)."""
    used = getattr(f, "sources_used", None) or []
    if not used:
        return "Windy + WRF-SMN"
    windy_order = ("windy_gfs", "windy_ecmwf", "windy_icon")
    windy_labels: list[str] = []
    wrf_label: Optional[str] = None
    for s in used:
        src = getattr(s, "value", s) if hasattr(s, "value") else str(s)
        if src == "wrf_smn":
            wrf_label = "WRF-SMN"
        elif src in _METEO_SOURCE_DISPLAY:
            windy_labels.append(_METEO_SOURCE_DISPLAY[src])
    parts: list[str] = []
    if windy_labels:
        ordered = [
            _METEO_SOURCE_DISPLAY[k]
            for k in windy_order
            if _METEO_SOURCE_DISPLAY.get(k) in windy_labels
        ]
        if not ordered:
            ordered = sorted(set(windy_labels))
        parts.append(" + ".join(ordered))
    if wrf_label:
        parts.append(wrf_label)
    return ", ".join(parts) if parts else "Windy + WRF-SMN"


def _unified_to_current_response(
    lat: float, lon: float, f: UnifiedForecast
) -> dict[str, Any]:
    """Mapea UnifiedForecast a la estructura que espera el frontend para current.
    La API devuelve valores en las unidades que usa el frontend (km/h para viento)
    para que todo el sistema use una sola fuente de verdad."""
    ts = f.timestamp.isoformat() if f.timestamp else None
    wind_ms = f.wind_speed_ms if f.wind_speed_ms is not None else 0
    wind_kmh = round(wind_ms * 3.6, 1)
    return {
        "location": {"lat": lat, "lon": lon},
        "current": {
            "temperature": f.temperature_celsius if f.temperature_celsius is not None else 0,
            "humidity": int(f.humidity_pct) if f.humidity_pct is not None else 0,
            "wind_speed": wind_ms,
            "wind_speed_kmh": wind_kmh,
            "wind_direction": _deg_to_cardinal(f.wind_direction_deg),
            "wind_direction_deg": int(f.wind_direction_deg) if f.wind_direction_deg is not None else None,
            "pressure": int(f.pressure_hpa) if f.pressure_hpa is not None else 1013,
            "conditions": _conditions_from_forecast(f),
            "precipitation": f.precipitation_mm if f.precipitation_mm is not None else 0,
            "cloud_cover": int(f.cloud_cover_pct) if f.cloud_cover_pct is not None else 0,
            "weather_code": 0,
            "timestamp": ts,
        },
        "source": "fused",
        "meteo_source_display": _meteo_source_display_from_unified(f),
        "authentication": "protected",
        "api_key_valid": True,
    }


def _unified_to_forecast_item(f: UnifiedForecast) -> dict[str, Any]:
    """Mapea un UnifiedForecast a un ítem del array forecast para el frontend.
    Incluye wind_speed_kmh para que el frontend use valores de la API sin convertir."""
    ts = f.timestamp.isoformat() if f.timestamp else ""
    wind_ms = f.wind_speed_ms if f.wind_speed_ms is not None else 0
    wind_kmh = round(wind_ms * 3.6, 1)
    return {
        "date": ts[:10] if ts else "",
        "timestamp": ts,
        "temperature": f.temperature_celsius if f.temperature_celsius is not None else 0,
        "precipitation": f.precipitation_mm if f.precipitation_mm is not None else 0,
        "wind_speed": wind_ms,
        "wind_speed_kmh": wind_kmh,
        "conditions": _conditions_from_forecast(f),
    }


@router.get("/public/health")
async def weather_service_health():
    """Public health check for weather service."""
    return {
        "status": "healthy",
        "service": "weather",
        "authentication": "protected_endpoints_require_auth",
    }


@router.get("/current")
async def get_current_weather(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    user_preferences: Optional[dict[str, Any]] = None,
    api_key: str = Depends(require_api_key),
):
    """Obtiene tiempo actual desde UnifiedWeatherEngine (Windy + WRF-SMN)."""

    try:
        logger.info("Weather requested for coordinates: lat=%s, lon=%s", lat, lon)
        engine = UnifiedWeatherEngine()
        unified = engine.get_current_unified(latitude=lat, longitude=lon)

        if unified is None:
            raise HTTPException(
                status_code=503,
                detail="No se pudieron obtener datos meteorológicos. Intente más tarde.",
            )

        return _unified_to_current_response(lat, lon, unified)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting current weather: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get weather data")


@router.get("/forecast")
async def get_weather_forecast(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(7, ge=1, le=14, description="Forecast days"),
    hours: Optional[int] = Query(None, ge=1, le=336, description="Forecast hours (alternativa a days)"),
    user_preferences: Optional[dict[str, Any]] = None,
    api_key: str = Depends(require_api_key),
):
    """Obtiene pronóstico desde UnifiedWeatherEngine (Windy + WRF-SMN)."""

    try:
        effective_hours = hours if hours is not None else days * 24
        logger.info(
            "Forecast requested for coordinates: lat=%s, lon=%s, hours=%s",
            lat, lon, effective_hours,
        )
        engine = UnifiedWeatherEngine()
        forecasts = engine.get_unified_forecast(
            latitude=lat,
            longitude=lon,
            hours=effective_hours,
        )

        if not forecasts:
            raise HTTPException(
                status_code=503,
                detail="No se pudieron obtener datos meteorológicos. Intente más tarde.",
            )

        return {
            "location": {"lat": lat, "lon": lon},
            "forecast_days": (effective_hours + 23) // 24,
            "authentication": "protected",
            "api_key_valid": True,
            "forecast": [_unified_to_forecast_item(f) for f in forecasts],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting weather forecast: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get forecast")


def _derive_visibility_ceiling_from_forecast(f: UnifiedForecast) -> tuple[float, Optional[float]]:
    """
    Deriva visibilidad (km) y techo (m) heurísticamente desde nubosidad y precipitación.
    Sin datos de visibilidad/techo reales; para uso con get_flight_category (M3).
    """
    cloud = f.cloud_cover_pct or 0.0
    precip = f.precipitation_mm or 0.0
    # Visibilidad: precip fuerte reduce; nubosidad muy alta reduce
    if precip >= 5.0:
        visibility_km = max(1.0, 10.0 - precip * 1.5)
    elif precip >= 2.0:
        visibility_km = max(2.0, 8.0 - cloud / 20.0)
    elif cloud >= 90:
        visibility_km = max(3.0, 10.0 - cloud / 10.0)
    elif cloud >= 70:
        visibility_km = max(5.0, 12.0 - cloud / 8.0)
    else:
        visibility_km = max(8.0, 15.0 - cloud / 5.0)
    # Techo: nubosidad alta → techo bajo (OMM/OHMC)
    if cloud >= 95:
        ceiling_m = 150.0
    elif cloud >= 80:
        ceiling_m = 300.0
    elif cloud >= 60:
        ceiling_m = 500.0
    elif cloud >= 40:
        ceiling_m = 1000.0
    else:
        ceiling_m = 2000.0
    return (visibility_km, ceiling_m)


@router.get("/flight-category")
async def get_flight_category_endpoint(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    api_key: str = Depends(require_api_key),
):
    """
    Categoría de vuelo OMM/OHMC (VFR/MVFR/IFR/LIFR) para lat/lon.
    Deriva visibilidad y techo heurísticamente desde tiempo actual (M3.2).
    """
    try:
        engine = UnifiedWeatherEngine()
        unified = engine.get_current_unified(latitude=lat, longitude=lon)
        if unified is None:
            raise HTTPException(
                status_code=503,
                detail="No se pudieron obtener datos meteorológicos.",
            )
        visibility_km, ceiling_m = _derive_visibility_ceiling_from_forecast(unified)
        category = get_flight_category(visibility_km, ceiling_m)
        return {
            "location": {"lat": lat, "lon": lon},
            "category": category,
            "visibility_km": round(visibility_km, 1),
            "ceiling_m": ceiling_m,
            "authentication": "protected",
            "api_key_valid": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting flight category: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get flight category")
