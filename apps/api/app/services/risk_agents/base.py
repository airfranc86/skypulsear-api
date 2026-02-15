"""Interfaz base para Risk Evaluation Agents.

Los agentes operan en background, no bloquean la API y solo exponen
flags o métricas. Ver .cursor/Docs/AUDITORIA-FASE-FEATURES-FIXES-RISK-AGENTS.md.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RiskAgent(Protocol):
    """Protocolo que debe cumplir todo Risk Evaluation Agent."""

    @property
    def name(self) -> str:
        """Nombre identificador del agente (para logs y métricas)."""
        ...

    def evaluate(self) -> dict[str, Any]:
        """
        Evalúa riesgo; no debe lanzar excepciones al cliente.

        Returns:
            Diccionario con flags/métricas (p. ej. confidence, flags).
        """
        ...


class BaseRiskAgent(ABC):
    """Clase base abstracta para agentes; implementa nombre común."""

    def __init__(self, agent_name: str) -> None:
        self._name = agent_name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def evaluate(self) -> dict[str, Any]:
        """Evalúa y retorna solo métricas/flags; no bloquea ni altera respuestas API."""
        ...
