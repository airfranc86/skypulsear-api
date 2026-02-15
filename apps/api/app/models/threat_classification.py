"""Contrato de salida del motor de clasificación de amenazas (M2).

Estructura de resultado interpretado: tipo, nivel, etiqueta, criterio usado.
Sin cambiar contratos públicos existentes; uso futuro en pipeline de alertas/patrones.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ThreatType(str, Enum):
    """Tipo de amenaza clasificada por el motor (heurística física + etiquetado)."""

    SHELF_CLOUD = "shelf_cloud"
    WALL_CLOUD = "wall_cloud"
    HAIL_PROXY = "hail_proxy"
    SEVERE_CONVECTION = "severe_convection"
    OTHER = "other"


class ClassifiedThreat(BaseModel):
    """
    Amenaza clasificada: salida del motor de clasificación (M2).

    - threat_type: Shelf/Wall Cloud, proxy granizo, etc.
    - level: 0–4 (alineado con AlertLevel SMN)
    - label: Texto corto para UI
    - criterion_used: Descripción del criterio aplicado (ej. "dBZ>55 bajo 0°C")
    - raw_hint: Opcional; datos crudos o referencias para validación (GOES-16, SINARAME)
    """

    threat_type: ThreatType
    level: int = Field(..., ge=0, le=4)
    label: str = Field(..., min_length=1)
    criterion_used: str = Field(default="", description="Criterio físico/heurístico aplicado")
    raw_hint: Optional[dict[str, Any]] = Field(default=None, description="Datos crudos para validación (opcional)")
