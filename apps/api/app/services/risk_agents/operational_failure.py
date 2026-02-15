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

    # Circuit conocido: se reporta aunque aún no esté registrado (p. ej. sin llamar a weather)
    KNOWN_CIRCUITS = ("windy_api",)

    def evaluate(self) -> dict[str, Any]:
        """
        Lee estados de circuit breakers registrados y expone métricas.
        Si ningún circuit está registrado aún, reporta KNOWN_CIRCUITS como cerrado (0).
        """
        result: dict[str, Any] = {"agent": self.name, "circuits": {}}
        try:
            states = get_circuit_states()
            for circuit_name, state in states:
                is_open = state == "open"
                record_risk_agent_circuit_open(circuit_name, is_open)
                result["circuits"][circuit_name] = state
            # Si el registro está vacío (nadie ha usado weather aún), exponer windy_api como 0
            if not states:
                for name in self.KNOWN_CIRCUITS:
                    record_risk_agent_circuit_open(name, False)
        except Exception as e:
            logger.warning("OperationalFailureRiskAgent: %s", e, exc_info=True)
            result["error"] = str(e)
        return result
