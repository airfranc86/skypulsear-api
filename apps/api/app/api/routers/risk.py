"""
Router de cálculo de riesgo por perfil.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from app.api.dependencies import require_api_key
from app.services import (
    AlertService,
    PatternDetector,
    RiskScoringService,
    UnifiedWeatherEngine,
    UserProfile,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class RiskScoreRequest(BaseModel):
    """Request para cálculo de risk score."""

    lat: float = Field(..., ge=-90, le=90, description="Latitud")
    lon: float = Field(..., ge=-180, le=180, description="Longitud")
    profile: str = Field(..., description="Tipo de perfil (piloto, agricultor, etc.)")
    hours_ahead: int = Field(6, ge=1, le=72, description="Horas a evaluar")


class RiskScoreResponse(BaseModel):
    """Response del cálculo de risk score."""

    score: float = Field(..., ge=0, le=5, description="Score de riesgo (0-5)")
    category: str = Field(..., description="Categoría de riesgo")
    risk_score_100: float = Field(
        ..., ge=0, le=100, description="Score convertido a 0-100"
    )
    temperature_risk: float = Field(..., ge=0, le=5)
    wind_risk: float = Field(..., ge=0, le=5)
    precipitation_risk: float = Field(..., ge=0, le=5)
    storm_risk: float = Field(..., ge=0, le=5)
    hail_risk: float = Field(..., ge=0, le=5)
    pattern_risk: float = Field(..., ge=0, le=5)
    alert_risk: float = Field(..., ge=0, le=5)
    apparent_temperature: Optional[float] = None
    recommendations: list[str] = Field(default_factory=list)
    key_factors: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)


@router.post("/risk-score", response_model=RiskScoreResponse)
async def calculate_risk_score(
    http_request: Request,
    request: RiskScoreRequest,
    api_key: str = Depends(require_api_key),
) -> RiskScoreResponse:
    """
    Calcula el risk score para un perfil específico.

    Integra:
    - UnifiedWeatherEngine: Obtiene pronóstico fusionado
    - PatternDetector: Detecta patrones meteorológicos
    - AlertService: Genera alertas operativas
    - RiskScoringService: Calcula score personalizado por perfil

    Perfiles disponibles:
    - piloto: Aviación general
    - agricultor: Agricultura y ganadería
    - camionero: Transporte terrestre
    - deporte_aire_libre: Deportes al aire libre
    - evento_exterior: Eventos al aire libre
    - construccion: Construcción
    - turismo: Turismo / Excursión
    - general: General
    """

    try:
        # Mapear string a UserProfile
        profile_map = {
            "piloto": UserProfile.PILOT,
            "agricultor": UserProfile.FARMER,
            "camionero": UserProfile.TRUCKER,
            "deporte_aire_libre": UserProfile.OUTDOOR_SPORTS,
            "evento_exterior": UserProfile.OUTDOOR_EVENT,
            "construccion": UserProfile.CONSTRUCTION,
            "turismo": UserProfile.TOURISM,
            "general": UserProfile.GENERAL,
        }

        profile = profile_map.get(request.profile.lower())
        if not profile:
            raise HTTPException(
                status_code=400,
                detail=f"Perfil no válido. Opciones: {list(profile_map.keys())}",
            )

        correlation_id = getattr(http_request.state, "correlation_id", None)

        logger.info(
            "Calculando risk score",
            extra={
                "profile": profile.value,
                "latitude": request.lat,
                "longitude": request.lon,
                "hours_ahead": request.hours_ahead,
                "correlation_id": correlation_id,
            },
        )

        # 1. Obtener pronóstico fusionado
        engine = UnifiedWeatherEngine()
        forecasts = engine.get_unified_forecast(
            latitude=request.lat,
            longitude=request.lon,
            hours=request.hours_ahead + 6,  # Obtener más horas para análisis
        )

        if not forecasts:
            raise HTTPException(
                status_code=503,
                detail="No se pudieron obtener datos meteorológicos. Intente más tarde.",
            )

        # 2. Detectar patrones
        pattern_detector = PatternDetector()
        patterns = pattern_detector.detect_patterns(forecasts)

        # 3. Generar alertas
        alert_service = AlertService()
        alerts = alert_service.generate_alerts(patterns, forecasts)

        # 4. Calcular risk score
        risk_service = RiskScoringService()
        risk_score = risk_service.calculate_risk(
            profile=profile,
            forecasts=forecasts,
            patterns=patterns,
            alerts=alerts,
            hours_ahead=request.hours_ahead,
        )

        # Convertir score 0-5 a 0-100 para frontend
        risk_score_100 = (risk_score.score / 5.0) * 100

        # Extraer recomendaciones de patrones y alertas
        recommendations = []
        if patterns:
            for pattern in patterns:
                recommendations.extend(pattern.recommendations)
        if alerts:
            for alert in alerts:
                if alert.recommendations:
                    recommendations.extend(alert.recommendations)

        # Generar key factors
        key_factors = []
        if risk_score.temperature_risk >= 3:
            key_factors.append(
                f"Riesgo térmico alto: {risk_score.temperature_risk:.1f}/5"
            )
        if risk_score.wind_risk >= 3:
            key_factors.append(f"Riesgo de viento: {risk_score.wind_risk:.1f}/5")
        if risk_score.precipitation_risk >= 3:
            key_factors.append(
                f"Riesgo de precipitación: {risk_score.precipitation_risk:.1f}/5"
            )
        if risk_score.storm_risk >= 3:
            key_factors.append(f"Riesgo de tormentas: {risk_score.storm_risk:.1f}/5")
        if patterns:
            key_factors.append(
                f"{len(patterns)} patrón(es) meteorológico(s) detectado(s)"
            )

        return RiskScoreResponse(
            score=risk_score.score,
            category=risk_score.category.value,
            risk_score_100=risk_score_100,
            temperature_risk=risk_score.temperature_risk,
            wind_risk=risk_score.wind_risk,
            precipitation_risk=risk_score.precipitation_risk,
            storm_risk=risk_score.storm_risk,
            hail_risk=risk_score.hail_risk,
            pattern_risk=risk_score.pattern_risk,
            alert_risk=risk_score.alert_risk,
            apparent_temperature=risk_score.apparent_temperature,
            recommendations=recommendations[:5],  # Limitar a 5 recomendaciones
            key_factors=key_factors[:5],  # Limitar a 5 factores
            confidence=risk_score.confidence,
        )
    except HTTPException:
        raise
    except Exception as e:
        correlation_id = getattr(http_request.state, "correlation_id", None)

        logger.error(
            "Error calculando risk score",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "profile": request.profile,
                "latitude": request.lat,
                "longitude": request.lon,
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        # Convertir errores de servicios externos a 503
        raise HTTPException(
            status_code=503,
            detail="Servicio temporalmente no disponible. Intente más tarde.",
        )
