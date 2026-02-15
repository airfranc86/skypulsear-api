"""Motor de clasificación de amenazas (M2). Lógica física y heurística Shelf/Wall/proxy granizo."""

from app.services.threat_classification.classifier import classify_threats
from app.services.threat_classification.inputs import ThreatClassificationInput

__all__ = ["classify_threats", "ThreatClassificationInput"]
