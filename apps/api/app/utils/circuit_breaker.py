"""Circuit breaker para proteger contra cascading failures en APIs externas."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from app.utils.exceptions import APIError, CircuitBreakerOpenError


class CircuitState(Enum):
    """Estados del circuit breaker."""

    CLOSED = "closed"  # Normal, permitir requests
    OPEN = "open"  # Fallando, rechazar requests inmediatamente
    HALF_OPEN = "half_open"  # Probando recuperación, permitir un request de prueba


class CircuitBreaker:
    """
    Circuit breaker para proteger contra cascading failures.

    Implementa el patrón circuit breaker:
    - CLOSED: Funcionamiento normal
    - OPEN: Después de N fallos consecutivos, rechaza requests
    - HALF_OPEN: Después de timeout, permite un request de prueba
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "circuit_breaker",
    ):
        """
        Inicializar circuit breaker.

        Args:
            failure_threshold: Número de fallos consecutivos antes de abrir
            recovery_timeout: Segundos antes de intentar recuperación (half-open)
            expected_exception: Tipo de excepción que cuenta como fallo
            name: Nombre del circuit breaker (para logging)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self.last_success_time: Optional[datetime] = None

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función con protección de circuit breaker.

        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales para la función
            **kwargs: Argumentos nombrados para la función

        Returns:
            Resultado de la función

        Raises:
            CircuitBreakerOpenError: Si el circuit breaker está abierto
            Exception: Si la función falla (y no es el tipo esperado)
        """
        # Verificar estado actual
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
                # Registrar métricas cuando entra en half-open
                try:
                    from app.utils.metrics import record_circuit_breaker_state

                    record_circuit_breaker_state(self.name, self.state.value)
                except ImportError:
                    pass
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {self.last_failure_time}"
                )

        # Intentar ejecutar la función
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
        except Exception as e:
            # Si no es el tipo esperado, no contar como fallo pero re-raise
            raise

    def _on_success(self) -> None:
        """Manejar éxito de la operación."""
        self.failure_count = 0
        self.last_success_time = datetime.now()
        previous_state = self.state
        self.state = CircuitState.CLOSED

        # Registrar métricas cuando el circuit breaker se cierra (recuperación)
        if previous_state != CircuitState.CLOSED:
            try:
                from app.utils.metrics import record_circuit_breaker_state

                record_circuit_breaker_state(self.name, self.state.value)
            except ImportError:
                # Métricas no disponibles (durante imports iniciales)
                pass

    def _on_failure(self) -> None:
        """Manejar fallo de la operación."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            # Registrar métricas cuando el circuit breaker se abre
            try:
                from app.utils.metrics import (
                    record_circuit_breaker_failure,
                    record_circuit_breaker_state,
                )

                record_circuit_breaker_failure(self.name)
                record_circuit_breaker_state(self.name, self.state.value)
            except ImportError:
                # Métricas no disponibles (durante imports iniciales)
                pass

    def _should_attempt_recovery(self) -> bool:
        """
        Determinar si se debe intentar recuperación (half-open).

        Returns:
            True si ha pasado suficiente tiempo desde el último fallo
        """
        if not self.last_failure_time:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure >= timedelta(seconds=self.recovery_timeout)

    def get_state(self) -> CircuitState:
        """
        Obtener estado actual del circuit breaker.

        Returns:
            Estado actual (CLOSED, OPEN, HALF_OPEN)
        """
        return self.state

    def get_metrics(self) -> dict[str, Any]:
        """
        Obtener métricas del circuit breaker.

        Returns:
            Diccionario con métricas (estado, fallos, último fallo, etc.)
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "last_success_time": (
                self.last_success_time.isoformat() if self.last_success_time else None
            ),
        }

    def reset(self) -> None:
        """Resetear circuit breaker a estado inicial (para testing)."""
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.state = CircuitState.CLOSED
