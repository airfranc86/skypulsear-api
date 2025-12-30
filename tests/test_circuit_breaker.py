"""Tests para circuit breaker."""

import pytest
from datetime import datetime, timedelta

from app.utils.circuit_breaker import CircuitBreaker, CircuitState
from app.utils.exceptions import CircuitBreakerOpenError


def test_circuit_breaker_initial_state():
    """Test que el circuit breaker inicia en estado CLOSED."""
    cb = CircuitBreaker(name="test_cb")
    assert cb.get_state() == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_success():
    """Test que un éxito resetea el contador de fallos."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=3)
    
    def success_func():
        return "success"
    
    result = cb.call(success_func)
    assert result == "success"
    assert cb.failure_count == 0
    assert cb.get_state() == CircuitState.CLOSED


def test_circuit_breaker_failure():
    """Test que un fallo incrementa el contador."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=3)
    
    def failing_func():
        raise ConnectionError("Connection failed")
    
    with pytest.raises(ConnectionError):
        cb.call(failing_func)
    
    assert cb.failure_count == 1
    assert cb.get_state() == CircuitState.CLOSED


def test_circuit_breaker_opens_after_threshold():
    """Test que el circuit breaker se abre después del threshold."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=3)
    
    def failing_func():
        raise ConnectionError("Connection failed")
    
    # Fallar 3 veces
    for _ in range(3):
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
    
    assert cb.failure_count == 3
    assert cb.get_state() == CircuitState.OPEN


def test_circuit_breaker_open_rejects_immediately():
    """Test que un circuit breaker abierto rechaza requests inmediatamente."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=2)
    
    def failing_func():
        raise ConnectionError("Connection failed")
    
    # Abrir el circuit breaker
    for _ in range(2):
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
    
    # Ahora debería estar abierto
    assert cb.get_state() == CircuitState.OPEN
    
    # Intentar llamar debería lanzar CircuitBreakerOpenError
    with pytest.raises(CircuitBreakerOpenError):
        cb.call(failing_func)


def test_circuit_breaker_half_open_recovery():
    """Test que el circuit breaker entra en half-open después del timeout."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout=1)
    
    def failing_func():
        raise ConnectionError("Connection failed")
    
    # Abrir el circuit breaker
    for _ in range(2):
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
    
    assert cb.get_state() == CircuitState.OPEN
    
    # Simular que pasó el recovery timeout
    cb.last_failure_time = datetime.now() - timedelta(seconds=2)
    
    # El siguiente call debería intentar half-open
    def success_func():
        return "success"
    
    result = cb.call(success_func)
    assert result == "success"
    assert cb.get_state() == CircuitState.CLOSED


def test_circuit_breaker_metrics():
    """Test que get_metrics retorna información correcta."""
    cb = CircuitBreaker(name="test_cb")
    
    metrics = cb.get_metrics()
    assert metrics["name"] == "test_cb"
    assert metrics["state"] == "closed"
    assert metrics["failure_count"] == 0


def test_circuit_breaker_reset():
    """Test que reset vuelve al estado inicial."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=2)
    
    def failing_func():
        raise ConnectionError("Connection failed")
    
    # Abrir el circuit breaker
    for _ in range(2):
        with pytest.raises(ConnectionError):
            cb.call(failing_func)
    
    assert cb.get_state() == CircuitState.OPEN
    
    # Reset
    cb.reset()
    
    assert cb.get_state() == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.last_failure_time is None

