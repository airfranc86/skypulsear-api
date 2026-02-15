"""
Router de cálculo de riesgo. Un solo perfil (general); el campo profile está deprecado.
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
    profile: str = Field(
        "general",
        description="Ignorado: se usa siempre perfil general. Mantenido por compatibilidad.",
    )
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
    Calcula el risk score (un solo perfil: general).

    Integra:
    - UnifiedWeatherEngine: pronóstico fusionado
    - PatternDetector: patrones meteorológicos
    - AlertService: alertas operativas
    - RiskScoringService: score de riesgo
    """

    try:
        # Un solo perfil: siempre GENERAL (campo profile en request ignorado)
        profile = UserProfile.GENERAL

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

        # Quick fix producción: devolver 200 con score por defecto en lugar de 503
        if not forecasts:
            logger.warning(
                "Sin datos meteorológicos; devolviendo risk score por defecto",
                extra={"latitude": request.lat, "longitude": request.lon},
            )
            return RiskScoreResponse(
                score=0.0,
                category="muy_bajo",
                risk_score_100=0.0,
                temperature_risk=0.0,
                wind_risk=0.0,
                precipitation_risk=0.0,
                storm_risk=0.0,
                hail_risk=0.0,
                pattern_risk=0.0,
                alert_risk=0.0,
                apparent_temperature=None,
                recommendations=["Datos meteorológicos no disponibles. Intente más tarde."],
                key_factors=[],
                confidence=0.0,
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
                if alert.recommendation:
                    recommendations.append(alert.recommendation)

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

        category_str = (
            risk_score.category.value
            if hasattr(risk_score.category, "value")
            else risk_score.category
        )
        # Servicio devuelve sub-scores en 0-100; API expone 0-5 para el frontend (que multiplica por 20 para barras)
        def to_api_scale(val: float) -> float:
            return round(val / 20.0, 1)

        return RiskScoreResponse(
            score=risk_score.score,
            category=category_str,
            risk_score_100=risk_score_100,
            temperature_risk=to_api_scale(float(risk_score.temperature_risk)),
            wind_risk=to_api_scale(float(risk_score.wind_risk)),
            precipitation_risk=to_api_scale(float(risk_score.precipitation_risk)),
            storm_risk=to_api_scale(float(risk_score.storm_risk)),
            hail_risk=to_api_scale(float(risk_score.hail_risk)),
            pattern_risk=to_api_scale(float(risk_score.pattern_risk)),
            alert_risk=to_api_scale(float(getattr(risk_score, "alert_risk", 0))),
            apparent_temperature=risk_score.apparent_temperature,
            recommendations=recommendations[:5],  # Limitar a 5 recomendaciones
            key_factors=key_factors[:5],  # Limitar a 5 factores
            confidence=getattr(risk_score, "confidence", 0.5),
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
