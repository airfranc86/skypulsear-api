"""
Weather Router (Simplified for Phase 1)

Weather endpoints with basic protection for Phase 1 security implementation.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Request

from app.api.dependencies import require_api_key

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
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    user_preferences: Optional[Dict[str, Any]] = None,
    api_key: str = Depends(require_api_key),
):
    """Get current weather - requires API key header."""

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
            "source": "windy",
            "authentication": "protected",
            "api_key_valid": True,
        }

        return weather_data

    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(status_code=500, detail="Failed to get weather data")


@router.get("/forecast")
async def get_weather_forecast(
    request: Request,
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    days: int = Query(7, ge=1, le=14, description="Forecast days"),
    user_preferences: Optional[Dict[str, Any]] = None,
    api_key: str = Depends(require_api_key),
):
    """Get weather forecast - requires API key."""

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


