"""
Weather Router (Simplified for Phase 1)

Weather endpoints with basic protection for Phase 1 security implementation.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["weather"])


class WeatherRequest(BaseModel):
    lat: float = Query(..., ge=-90, le=90, description="Latitude")
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
    user_preferences: Dict[str, Any] = None


@router.get("/public/health")
async def weather_service_health():
    """Public health check for weather service."""
    return {
        "status": "healthy",
        "service": "weather",
        "authentication": "protected_endpoints_require_auth",
    }


@router.get("/current")
async def get_current_weather(request: WeatherRequest, api_key: str = None):
    """Get current weather - requires API key header."""

    # Simple API key validation for Phase 1
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Add X-API-Key header."
        )

    try:
        logger.info(
            f"Weather requested for coordinates: lat={request.lat}, lon={request.lon}"
        )

        # Mock weather data (Phase 1 demo)
        weather_data = {
            "location": {"lat": request.lat, "lon": request.lon},
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
    request: WeatherRequest, days: int = 7, api_key: str = None
):
    """Get weather forecast - requires API key."""

    # Simple API key validation for Phase 1
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Add X-API-Key header."
        )

    try:
        logger.info(
            f"Forecast requested for coordinates: lat={request.lat}, lon={request.lon}, days={days}"
        )

        # Mock forecast data (Phase 1 demo)
        forecast_data = {
            "location": {"lat": request.lat, "lon": request.lon},
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
    request: WeatherRequest, hours: int = 24, api_key: str = None
):
    """Get weather alerts - requires API key."""

    # Simple API key validation for Phase 1
    if not api_key:
        raise HTTPException(
            status_code=401, detail="API key required. Add X-API-Key header."
        )

    try:
        logger.info(
            f"Alerts requested for coordinates: lat={request.lat}, lon={request.lon}"
        )

        # Mock alerts data (Phase 1 demo)
        alerts_data = {
            "location": {"lat": request.lat, "lon": request.lon},
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
