"""
Weather Router (Simplified for Phase 1)

Weather endpoints with basic protection for Phase 1 security implementation.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["weather"])


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
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    user_preferences: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
):
    """Get current weather - requires API key header."""

    # Simple API key validation for Phase 1
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Add X-API-Key header."
        )

    try:
        logger.info(f"Weather requested for coordinates: lat={lat}, lon={lon}")

        # Mock weather data (Phase 1 demo)
        weather_data = {
            "location": {"lat": lat, "lon": lon},
            "current": {
                "temperature": 22.5,
                "humidity": 65,
                "wind_speed": 12,
                "wind_direction": "NE",
                "pressure": 1013,
                "conditions": "partly cloudy",
            },
            "source": "open-meteo",
            "authentication": "protected",
            "api_key_valid": True,
        }

        return weather_data

    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(status_code=500, detail="Failed to get weather data")


@router.get("/forecast")
async def get_weather_forecast(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(7, ge=1, le=14, description="Forecast days"),
    user_preferences: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
):
    """Get weather forecast - requires API key."""

    # Simple API key validation for Phase 1
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Add X-API-Key header."
        )

    try:
        logger.info(
            f"Forecast requested for coordinates: lat={lat}, lon={lon}, days={days}"
        )

        # Mock forecast data (Phase 1 demo)
        forecast_data = {
            "location": {"lat": lat, "lon": lon},
            "forecast_days": days,
            "authentication": "protected",
            "api_key_valid": True,
            "forecast": [
                {
                    "date": f"2024-01-{i + 1:02d}",
                    "high": 28 + i,
                    "low": 18 + i,
                    "conditions": "variable clouds",
                }
                for i in range(min(days, 5))
            ],
        }

        return forecast_data

    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}")
        raise HTTPException(status_code=500, detail="Failed to get forecast")


@router.get("/alerts")
async def get_weather_alerts(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    user_preferences: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
):
    """Get weather alerts - requires API key."""

    # Simple API key validation for Phase 1
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Add X-API-Key header."
        )

    try:
        logger.info(f"Alerts requested for coordinates: lat={lat}, lon={lon}")

        # Mock alerts data (Phase 1 demo)
        alerts_data = {
            "location": {"lat": lat, "lon": lon},
            "time_window_hours": hours,
            "authentication": "protected",
            "api_key_valid": True,
            "alerts": [
                {
                    "type": "wind",
                    "severity": "moderate",
                    "title": "Vientos Fuertes",
                    "description": "Se esperan vientos de hasta 45 km/h",
                    "valid_from": "2024-01-06T12:00:00Z",
                    "valid_until": "2024-01-06T18:00:00Z",
                }
            ],
        }

        return alerts_data

    except Exception as e:
        logger.error(f"Error getting weather alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")
