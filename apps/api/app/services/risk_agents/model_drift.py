"""Model Drift Risk Agent.

Detecta divergencia entre modelo y observación; evalúa degradación de skill score.
Solo emite bandera de confianza/métrica; no bloquea API. Requiere fuente de observación.
"""

import logging
from typing import Any

from app.services.risk_agents.base import BaseRiskAgent

logger = logging.getLogger(__name__)


class ModelDriftRiskAgent(BaseRiskAgent):
    """
    Evalúa drift del modelo (p. ej. GFS vía Windy) frente a observación.

    Emite skypulse_risk_agent_model_drift_confidence cuando hay observación.
    Sin fuente de observación, no actualiza la métrica (skeleton).
    """

    def __init__(self) -> None:
        super().__init__("model_drift")

    def evaluate(self) -> dict[str, Any]:
        """
        Evalúa drift; sin fuente de observación no actualiza métrica.
        Futuro: comparar salida del modelo con observación y emitir skill.
        """
        result: dict[str, Any] = {"agent": self.name, "status": "no_observation", "confidence": None}
        # Sin observación no setear métrica (evitar 0 que podría interpretarse como drift)
        return result
