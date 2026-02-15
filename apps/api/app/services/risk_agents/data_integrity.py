"""Data Integrity Risk Agent.

Detecta datos incompletos, latencia excesiva, inconsistencias temporales.
Solo flags/métricas; no bloquea requests.
"""

import logging
from typing import Any

from app.services.risk_agents.base import BaseRiskAgent
from app.utils.metrics import risk_agent_data_integrity_ok

logger = logging.getLogger(__name__)


class DataIntegrityRiskAgent(BaseRiskAgent):
    """
    Evalúa integridad de datos ingeridos: completitud, latencia, coherencia temporal.

    Ejecución periódica o post-ingesta; sin bloqueo de API.
    Expone skypulse_risk_agent_data_integrity_ok (1=ok, 0=problemas).
    """

    def __init__(self) -> None:
        super().__init__("data_integrity")

    def evaluate(self) -> dict[str, Any]:
        """
        Evalúa integridad; por ahora sin fuente de datos, marca 1 (ok).
        Futuro: comprobar completitud/latencia de datos ya obtenidos; solo entonces set(0).
        """
        result: dict[str, Any] = {"agent": self.name, "completeness_ok": True}
        try:
            # Sin lógica de comprobación aún; solo exponer métrica (1 = ok)
            risk_agent_data_integrity_ok.set(1)
        except Exception as e:
            logger.warning("DataIntegrityRiskAgent: %s", e, exc_info=True)
            result["error"] = str(e)
            # No set(0) en excepción: 0 solo cuando detectemos problema de integridad real
        return result
