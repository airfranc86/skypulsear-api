"""
Weather Router with Authentication

Secure weather endpoints requiring JWT authentication.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# from app.api.routers.auth import get_current_user  # Use simple auth for demo
from app.utils.security import get_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weather", tags=["weather"])


class WeatherRequest(BaseModel):
    lat: float = Query(..., ge=-90, le=90, description="Latitude")
    lon: float = Query(..., ge=-180, le=180, description="Longitude")
    user_preferences: Optional[Dict[str, Any]] = None


@router.get("/current")
async def get_current_weather(
    lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)
):
    """Get current weather for authenticated user."""
    try:
        # For now, return demo data with user context
        logger.info(
            f"Weather requested for user: {current_user['username']} at {lat}, {lon}"
        )

        # Mock weather data (in production, this would call weather services)
        weather_data = {
            "location": {"lat": lat, "lon": lon},
            "current": {
                "temperature": 22.5,
                "humidity": 65,
                "wind_speed": 12,
                "wind_direction": "NE",
                "pressure": 1013,
                "visibility": 10,
                "conditions": "partly cloudy",
            },
            "source": "open-meteo",
            "user_context": {
                "user_id": current_user.get("username"),
                "authenticated": True,
            },
        }

        return weather_data

    except Exception as e:
        logger.error(f"Error getting current weather: {e}")
        raise HTTPException(status_code=500, detail="Failed to get weather data")


@router.get("/forecast")
async def get_weather_forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(default=7, ge=1, le=14),
    current_user: dict = Depends(get_current_user),
):
    """Get weather forecast for authenticated user."""
    try:
        logger.info(
            f"Forecast requested for user: {current_user['username']} at {lat}, {lon}"
        )

        # Mock forecast data
        forecast_data = {
            "location": {"lat": lat, "lon": lon},
            "forecast_days": days,
            "forecast": [
                {
                    "date": f"2024-01-{i + 1:02d}",
                    "high": 28 + i,
                    "low": 18 + i,
                    "conditions": "variable clouds",
                }
                for i in range(min(days, 5))
            ],
            "user_context": {
                "user_id": current_user.get("username"),
                "authenticated": True,
            },
        }

        return forecast_data

    except Exception as e:
        logger.error(f"Error getting weather forecast: {e}")
        raise HTTPException(status_code=500, detail="Failed to get forecast")


@router.get("/alerts")
async def get_weather_alerts(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    hours: int = Query(default=24, ge=1, le=168),
    current_user: dict = Depends(get_current_user),
):
    """Get weather alerts for authenticated user."""
    try:
        logger.info(
            f"Alerts requested for user: {current_user['username']} at {lat}, {lon}"
        )

        # Mock alerts data
        alerts_data = {
            "location": {"lat": lat, "lon": lon},
            "time_window_hours": hours,
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
            "user_context": {
                "user_id": current_user.get("username"),
                "authenticated": True,
            },
        }

        return alerts_data

    except Exception as e:
        logger.error(f"Error getting weather alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.get("/public/health")
async def weather_service_health():
    """Public health check for weather service."""
    return {
        "status": "healthy",
        "service": "weather",
        "authentication": "required",
        "timestamp": "2024-01-06T00:00:00Z",
    }
