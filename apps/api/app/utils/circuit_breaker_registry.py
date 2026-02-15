"""Registro voluntario de circuit breakers para Risk Agents.

Los repositorios registran su circuit breaker aquí; el Operational Failure Risk Agent
lee estados y expone métricas skypulse_risk_agent_*. No modifica el core.
"""

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from app.utils.circuit_breaker import CircuitBreaker

_registry: dict[str, "CircuitBreaker"] = {}


def register_circuit_breaker(name: str, circuit_breaker: "CircuitBreaker") -> None:
    """Registra un circuit breaker para que el agente de fallo operativo lo lea."""
    _registry[name] = circuit_breaker


def get_circuit_states() -> List[Tuple[str, str]]:
    """
    Retorna (nombre, estado) de cada circuit breaker registrado.
    Estado: "closed", "open", "half_open".
    """
    result: List[Tuple[str, str]] = []
    for name, cb in _registry.items():
        result.append((name, cb.get_state().value))
    return result
