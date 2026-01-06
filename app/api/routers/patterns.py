"""
Router de detección de patrones meteorológicos argentinos.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.services import PatternDetector, UnifiedWeatherEngine
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class PatternResponse(BaseModel):
    """Response de patrón detectado."""

    pattern_type: str
    risk_level: str
    confidence: float = Field(..., ge=0, le=1)
    title: str
    description: str
    trigger_values: dict[str, float] = Field(default_factory=dict)
    thresholds_exceeded: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class PatternsResponse(BaseModel):
    """Response de patrones detectados."""

    location: dict[str, float]
    patterns: list[PatternResponse]
    pattern_count: int
    max_risk_level: str


@router.get("/", response_model=PatternsResponse)
async def get_detected_patterns(
    request: Request,
    lat: float = Query(..., description="Latitud", ge=-90, le=90),
    lon: float = Query(..., description="Longitud", ge=-180, le=180),
    hours: int = Query(72, description="Horas a analizar", ge=1, le=168),
) -> PatternsResponse:
    """
    Detecta patrones meteorológicos argentinos para una ubicación.

    Patrones detectados:
    - Tormenta Convectiva Severa: CAPE alto, precipitación intensa
    - Ola de Calor: Temperatura > 35°C sostenida
    - Ola de Frío: Temperatura < 5°C sostenida
    - Helada: Temperatura < 0°C, cielo despejado

    Patrones pendientes de implementar:
    - Zonda: Viento cálido y seco del oeste (Cuyo)
    - Sudestada: Viento del SE con lluvia persistente (Buenos Aires)
    - Pampero: Viento frío del SW
    """
    try:
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.info(
            "Detectando patrones",
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
            hours=hours,
        )

        if not forecasts:
            raise HTTPException(
                status_code=503,
                detail="No se pudieron obtener datos meteorológicos. Intente más tarde.",
            )

        # 2. Detectar patrones
        detector = PatternDetector()
        patterns = detector.detect_patterns(forecasts)

        # Convertir a formato de respuesta
        pattern_responses = []
        max_risk = "bajo"

        for pattern in patterns:
            pattern_responses.append(
                PatternResponse(
                    pattern_type=pattern.pattern_type.value,
                    risk_level=pattern.risk_level.value,
                    confidence=pattern.confidence,
                    title=pattern.title,
                    description=pattern.description,
                    trigger_values=pattern.trigger_values,
                    thresholds_exceeded=pattern.thresholds_exceeded,
                    recommendations=pattern.recommendations,
                )
            )

            # Determinar riesgo máximo
            if pattern.risk_level.value == "extremo":
                max_risk = "extremo"
            elif pattern.risk_level.value == "alto" and max_risk not in ["extremo"]:
                max_risk = "alto"
            elif pattern.risk_level.value == "moderado" and max_risk not in [
                "extremo",
                "alto",
            ]:
                max_risk = "moderado"

        return PatternsResponse(
            location={"lat": lat, "lon": lon},
            patterns=pattern_responses,
            pattern_count=len(pattern_responses),
            max_risk_level=max_risk,
        )
    except HTTPException:
        raise
    except Exception as e:
        correlation_id = getattr(request.state, "correlation_id", None)

        logger.error(
            "Error detectando patrones",
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


@router.get("/types")
async def get_pattern_types() -> dict:
    """
    Lista todos los tipos de patrones meteorológicos detectables.
    """
    return {
        "patterns": [
            {
                "id": "zonda",
                "name": "Zonda",
                "description": "Viento cálido y seco del oeste, típico de Cuyo",
                "regions": ["mendoza", "san_juan", "la_rioja"],
            },
            {
                "id": "sudestada",
                "name": "Sudestada",
                "description": "Viento del SE con lluvia persistente",
                "regions": ["buenos_aires", "la_plata", "rio_de_la_plata"],
            },
            {
                "id": "pampero",
                "name": "Pampero",
                "description": "Viento frío del SW, cambio brusco de temperatura",
                "regions": ["pampa", "buenos_aires", "cordoba"],
            },
            {
                "id": "tormenta_convectiva",
                "name": "Tormenta Convectiva Severa",
                "description": "Tormentas con alto CAPE, posible granizo",
                "regions": ["cordoba", "santa_fe", "entre_rios"],
            },
            {
                "id": "ola_calor",
                "name": "Ola de Calor",
                "description": "Temperatura > 35°C durante varios días",
                "regions": ["todo_el_pais"],
            },
            {
                "id": "ola_frio",
                "name": "Ola de Frío",
                "description": "Temperatura muy por debajo del promedio",
                "regions": ["todo_el_pais"],
            },
            {
                "id": "helada",
                "name": "Helada",
                "description": "Temperatura < 0°C con cielo despejado",
                "regions": ["pampa", "patagonia", "cuyo"],
            },
        ]
    }
