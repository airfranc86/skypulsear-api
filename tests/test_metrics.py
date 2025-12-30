"""Tests para métricas de Prometheus."""

import pytest
from app.utils.metrics import (
    record_request_metrics,
    record_source_availability,
    record_circuit_breaker_state,
    record_circuit_breaker_failure,
    get_metrics,
)


def test_record_request_metrics():
    """Test que se registran métricas de requests."""
    record_request_metrics("GET", "/api/v1/weather/current", 200, 0.5)
    
    # Verificar que las métricas se registraron (no hay excepción)
    metrics = get_metrics()
    assert b"http_requests_total" in metrics
    assert b"http_request_duration_seconds" in metrics


def test_record_source_availability():
    """Test que se registra disponibilidad de fuentes."""
    record_source_availability("meteosource", True)
    record_source_availability("windy", False)
    
    metrics = get_metrics()
    assert b"weather_source_availability" in metrics


def test_record_circuit_breaker_state():
    """Test que se registra estado de circuit breaker."""
    record_circuit_breaker_state("meteosource_api", "closed")
    record_circuit_breaker_state("windy_api", "open")
    
    metrics = get_metrics()
    assert b"circuit_breaker_state" in metrics


def test_record_circuit_breaker_failure():
    """Test que se registran fallos de circuit breaker."""
    record_circuit_breaker_failure("meteosource_api")
    
    metrics = get_metrics()
    assert b"circuit_breaker_failures_total" in metrics


def test_get_metrics_returns_bytes():
    """Test que get_metrics retorna bytes en formato Prometheus."""
    metrics = get_metrics()
    assert isinstance(metrics, bytes)
    assert len(metrics) > 0

