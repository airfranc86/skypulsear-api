"""Risk Evaluation Agents.

Agentes que evalúan riesgo en background (Model Drift, Data Integrity, Operational Failure).
No bloquean la API; solo exponen flags o métricas. Activación por RISK_AGENTS_ENABLED.

Ver .cursor/Docs/AUDITORIA-FASE-FEATURES-FIXES-RISK-AGENTS.md.
"""

import logging
import os
from typing import Any

from app.services.risk_agents.base import BaseRiskAgent, RiskAgent
from app.services.risk_agents.operational_failure import OperationalFailureRiskAgent
from app.services.risk_agents.data_integrity import DataIntegrityRiskAgent
from app.services.risk_agents.model_drift import ModelDriftRiskAgent

_logger = logging.getLogger(__name__)


def is_risk_agents_enabled() -> bool:
    """Feature toggle global: activa o desactiva la ejecución de Risk Agents."""
    return os.getenv("RISK_AGENTS_ENABLED", "false").strip().lower() == "true"


def get_risk_agents() -> list[RiskAgent]:
    """Retorna la lista de agentes (para ejecución en background)."""
    return [
        OperationalFailureRiskAgent(),
        DataIntegrityRiskAgent(),
        ModelDriftRiskAgent(),
    ]


def run_risk_agents_safe() -> list[dict[str, Any]]:
    """
    Ejecuta todos los agentes solo si RISK_AGENTS_ENABLED=true.
    Si un agente falla, se registra y no se propaga; retorna resultados parciales.
    """
    if not is_risk_agents_enabled():
        return []
    results: list[dict[str, Any]] = []
    for agent in get_risk_agents():
        try:
            results.append(agent.evaluate())
        except Exception as e:  # Degradación silenciosa (RFC: no propagar al request)
            _logger.warning("Risk agent %s failed: %s", agent.name, e, exc_info=True)
    return results


__all__ = [
    "RiskAgent",
    "BaseRiskAgent",
    "OperationalFailureRiskAgent",
    "DataIntegrityRiskAgent",
    "ModelDriftRiskAgent",
    "is_risk_agents_enabled",
    "get_risk_agents",
    "run_risk_agents_safe",
]
