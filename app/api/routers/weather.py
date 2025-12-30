"""
Router de endpoints meteorológicos.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.data.schemas.normalized_weather import UnifiedForecast
from app.services import UnifiedWeatherEngine
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class CurrentWeatherResponse(BaseModel):
    """Response de datos meteorológicos actuales."""

    location: dict[str, float]
    timestamp: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    precipitation: Optional[float] = None
    cloud_cover: Optional[float] = None
    pressure: Optional[float] = None
    weather_code: Optional[int] = None
    confidence: float
    sources: list[str]


class ForecastResponse(BaseModel):
    """Response de pronóstico."""

    location: dict[str, float]
    hours: int
    forecast: list[dict]
    confidence: float
    sources: list[str]


@router.get("/current", response_model=CurrentWeatherResponse)
async def get_current_weather(
    request: Request,
    lat: float = Query(..., description="Latitud", ge=-90, le=90),
    lon: float = Query(..., description="Longitud", ge=-180, le=180),
) -> CurrentWeatherResponse:
    """
    Obtiene datos meteorológicos actuales fusionados.

    Combina múltiples fuentes: Meteosource, Windy (ECMWF/GFS/ICON), WRF-SMN.
    Retorna el pronóstico más cercano a la hora actual (forecast_hour=0).
    """
    try:
        correlation_id = getattr(request.state, "correlation_id", None)
        
        logger.info(
            "Obteniendo datos actuales",
            extra={
                "latitude": lat,
                "longitude": lon,
                "correlation_id": correlation_id,
            },
        )

        # Verificar repositorios disponibles
        from app.data.repositories.repository_factory import RepositoryFactory
        factory = RepositoryFactory()
        available_repos = list(factory.get_all_repositories().keys())
        logger.info(
            "Repositorios disponibles",
            extra={
                "available_repos": available_repos,
                "correlation_id": correlation_id,
            },
        )
        
        if not available_repos:
            logger.error(
                "No hay repositorios disponibles",
                extra={
                    "correlation_id": correlation_id,
                },
            )
            raise HTTPException(
                status_code=503,
                detail="No hay fuentes de datos configuradas. Verificar API keys.",
            )

        engine = UnifiedWeatherEngine()
        forecasts = engine.get_unified_forecast(
            latitude=lat,
            longitude=lon,
            hours=1,  # Solo necesitamos el actual
        )

        if not forecasts:
            logger.warning(
                "No se obtuvieron pronósticos",
                extra={
                    "available_repos": available_repos,
                    "correlation_id": correlation_id,
                },
            )
            raise HTTPException(
                status_code=503,
                detail=f"No se pudieron obtener datos meteorológicos. Repositorios disponibles: {', '.join(available_repos)}",
            )

        # Obtener el pronóstico actual (forecast_hour=0 o el más cercano)
        current = forecasts[0] if forecasts else None
        if not current:
            raise HTTPException(
                status_code=503,
                detail="No hay datos disponibles para la hora actual.",
            )

        # Extraer fuentes utilizadas
        sources = []
        if current.sources_used:
            sources = [source.value for source in current.sources_used]
        else:
            sources = ["fused"]  # Fallback

        return CurrentWeatherResponse(
            location={"lat": lat, "lon": lon},
            timestamp=current.timestamp.isoformat(),
            temperature=current.temperature_celsius,
            humidity=current.humidity_pct,
            wind_speed=current.wind_speed_ms,
            wind_direction=current.wind_direction_deg,
            precipitation=current.precipitation_mm,
            cloud_cover=current.cloud_cover_pct,
            pressure=current.pressure_hpa,
            weather_code=None,  # No está en UnifiedForecast
            confidence=current.overall_confidence,
            sources=sources,
        )
    except HTTPException:
        raise
    except Exception as e:
        # Obtener correlation ID del request state
        correlation_id = getattr(request.state, "correlation_id", None)
        
        logger.error(
            "Error obteniendo datos actuales",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "latitude": lat,
                "longitude": lon,
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        # No exponer detalles internos - el exception handler global se encargará
        raise


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    request: Request,
    lat: float = Query(..., description="Latitud", ge=-90, le=90),
    lon: float = Query(..., description="Longitud", ge=-180, le=180),
    hours: int = Query(24, description="Horas de pronóstico", ge=1, le=168),
) -> ForecastResponse:
    """
    Obtiene pronóstico fusionado de múltiples modelos.

    - 0-72h: Mayor peso a WRF-SMN (alta resolución)
    - 3-10 días: Mayor peso a ECMWF

    Retorna pronóstico horario para las próximas N horas.
    """
    try:
        correlation_id = getattr(request.state, "correlation_id", None)
        
        logger.info(
            "Obteniendo pronóstico",
            extra={
                "latitude": lat,
                "longitude": lon,
                "hours": hours,
                "correlation_id": correlation_id,
            },
        )

        engine = UnifiedWeatherEngine()
        forecasts = engine.get_unified_forecast(
            latitude=lat,
            longitude=lon,
            hours=hours,
        )

        if not forecasts:
            raise HTTPException(
                status_code=503,
                detail="No se pudieron obtener datos meteorológicos. Intente más tarde.",
            )

        # Convertir forecasts a formato dict para respuesta
        forecast_list = []
        sources_set = set()
        confidences = []

        for f in forecasts[:hours]:  # Limitar a las horas solicitadas
            forecast_dict = {
                "timestamp": f.timestamp.isoformat(),
                "forecast_hour": f.forecast_hour,
                "temperature": f.temperature_celsius,
                "humidity": f.humidity_pct,
                "wind_speed": f.wind_speed_ms,
                "wind_direction": f.wind_direction_deg,
                "precipitation": f.precipitation_mm,
                "cloud_cover": f.cloud_cover_pct,
                "pressure": f.pressure_hpa,
                "confidence": f.overall_confidence,
            }

            forecast_list.append(forecast_dict)
            confidences.append(f.overall_confidence)

            # Extraer fuentes
            if f.sources_used:
                for source in f.sources_used:
                    sources_set.add(source.value)

        # Calcular confianza promedio
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8

        return ForecastResponse(
            location={"lat": lat, "lon": lon},
            hours=hours,
            forecast=forecast_list,
            confidence=avg_confidence,
            sources=list(sources_set) if sources_set else ["fused"],
        )
    except HTTPException:
        raise
    except Exception as e:
        # Obtener correlation ID del request state
        correlation_id = getattr(request.state, "correlation_id", None)
        
        logger.error(
            "Error obteniendo pronóstico",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "latitude": lat,
                "longitude": lon,
                "hours": hours,
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        # No exponer detalles internos - el exception handler global se encargará
        raise
