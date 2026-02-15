"""Operational Failure Risk Agent.

Detecta caída de proveedor externo, latencia acumulada, estado de circuit breaker.
Solo expone métricas; no altera contrato API. Ejecución en background.
"""

import logging
from typing import Any

from app.services.risk_agents.base import BaseRiskAgent
from app.utils.circuit_breaker_registry import get_circuit_states
from app.utils.metrics import record_risk_agent_circuit_open

logger = logging.getLogger(__name__)


class OperationalFailureRiskAgent(BaseRiskAgent):
    """
    Evalúa riesgo operativo: estado de proveedores externos y circuit breaker.

    Lee estados del registro voluntario (Windy y futuros proveedores) y expone
    métricas skypulse_risk_agent_circuit_open. No bloquea la API.
    """

    def __init__(self) -> None:
        super().__init__("operational_failure")

    def evaluate(self) -> dict[str, Any]:
        """
        Lee estados de circuit breakers registrados y expone métricas.

        Returns:
            Dict con circuit_name -> state (closed|open|half_open).
        """
        result: dict[str, Any] = {"agent": self.name, "circuits": {}}
        try:
            for circuit_name, state in get_circuit_states():
                is_open = state == "open"
                record_risk_agent_circuit_open(circuit_name, is_open)
                result["circuits"][circuit_name] = state
        except Exception as e:
            logger.warning("OperationalFailureRiskAgent: %s", e, exc_info=True)
            result["error"] = str(e)
        return result
