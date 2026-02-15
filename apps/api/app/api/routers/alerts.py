"""
Router de alertas meteorológicas.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import require_api_key
from app.services import (
    AlertLevel,
    AlertService,
    PatternDetector,
    UnifiedWeatherEngine,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class AlertResponse(BaseModel):
    """Response de alerta individual."""

    level: int = Field(..., ge=0, le=4)
    level_name: str
    phenomenon: str
    title: str
    description: str
    time_window: str
    recommendations: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


class AlertsResponse(BaseModel):
    """Response de alertas para una ubicación."""

    location: dict[str, float]
    alerts: list[AlertResponse]
    alert_count: int
    max_level: int = Field(..., ge=0, le=4)
    max_level_name: str


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    request: Request,
    lat: float = Query(..., description="Latitud", ge=-90, le=90),
    lon: float = Query(..., description="Longitud", ge=-180, le=180),
    hours: int = Query(24, description="Horas a evaluar", ge=1, le=72),
    api_key: str = Depends(require_api_key),
) -> AlertsResponse:
    """
    Obtiene alertas meteorológicas activas para una ubicación.

    Niveles de alerta (compatibles con SMN Argentina):
    - 0: NORMAL - Sin alertas
    - 1: ATENCIÓN - Información general
    - 2: PRECAUCIÓN - Precaución recomendada
    - 3: ALERTA - Acción requerida
    - 4: CRÍTICA - Emergencia
    """

    try:
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.info(
            "Obteniendo alertas",
            extra={
                "latitude": lat,
                "longitude": lon,
                "hours": hours,
                "correlation_id": correlation_id,
            },
        )

        # 1. Obtener pronóstico fusionado
        engine = UnifiedWeatherEngine()
        forecasts = engine.get_unified_forecast(
            latitude=lat,
            longitude=lon,
            hours=hours + 6,  # Obtener más horas para análisis
        )

        if not forecasts:
            return AlertsResponse(
                location={"lat": lat, "lon": lon},
                alerts=[],
                alert_count=0,
                max_level=0,
                max_level_name="NORMAL",
            )

        # 2. Detectar patrones
        pattern_detector = PatternDetector()
        patterns = pattern_detector.detect_patterns(forecasts)

        # 3. Generar alertas
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(patterns, forecasts)

        # Convertir a formato de respuesta
        alert_responses = []
        max_level = 0

        for alert in alerts:
            # OperationalAlert no tiene title ni confidence; se derivan para AlertResponse
            title = f"{alert.level_name}: {alert.phenomenon}"
            alert_responses.append(
                AlertResponse(
                    level=alert.level,
                    level_name=alert.level_name,
                    phenomenon=alert.phenomenon,
                    title=title,
                    description=alert.description,
                    time_window=alert.time_window,
                    recommendations=[alert.recommendation] if alert.recommendation else [],
                    confidence=1.0,
                )
            )

            if alert.level > max_level:
                max_level = alert.level

        # Obtener nombre del nivel máximo
        max_level_name = AlertService.LEVEL_NAMES.get(AlertLevel(max_level), "NORMAL")

        return AlertsResponse(
            location={"lat": lat, "lon": lon},
            alerts=alert_responses,
            alert_count=len(alert_responses),
            max_level=max_level,
            max_level_name=max_level_name,
        )
    except HTTPException:
        raise
    except Exception as e:
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.error(
            "Error obteniendo alertas",
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
        # Convertir errores de servicios externos a 503
        raise HTTPException(
            status_code=503,
            detail="Servicio temporalmente no disponible. Intente más tarde.",
        )
