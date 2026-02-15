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


def _unified_to_current_response(
    lat: float, lon: float, f: UnifiedForecast
) -> dict[str, Any]:
    """Mapea UnifiedForecast a la estructura que espera el frontend para current."""
    return {
        "location": {"lat": lat, "lon": lon},
        "current": {
            "temperature": f.temperature_celsius if f.temperature_celsius is not None else 0,
            "humidity": int(f.humidity_pct) if f.humidity_pct is not None else 0,
            "wind_speed": f.wind_speed_ms if f.wind_speed_ms is not None else 0,
            "wind_direction": _deg_to_cardinal(f.wind_direction_deg),
            "pressure": int(f.pressure_hpa) if f.pressure_hpa is not None else 1013,
            "conditions": _conditions_from_forecast(f),
        },
        "source": "fused",
        "authentication": "protected",
        "api_key_valid": True,
    }


def _unified_to_forecast_item(f: UnifiedForecast) -> dict[str, Any]:
    """Mapea un UnifiedForecast a un ítem del array forecast para el frontend."""
    ts = f.timestamp.isoformat() if f.timestamp else ""
    return {
        "date": ts[:10] if ts else "",
        "timestamp": ts,
        "temperature": f.temperature_celsius if f.temperature_celsius is not None else 0,
        "precipitation": f.precipitation_mm if f.precipitation_mm is not None else 0,
        "wind_speed": f.wind_speed_ms if f.wind_speed_ms is not None else 0,
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
