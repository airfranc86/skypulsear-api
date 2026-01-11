"""Métricas de observabilidad usando Prometheus."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from typing import Optional

# Métricas de latencia HTTP
request_duration = Histogram(
    "http_request_duration_seconds",
    "Duración de requests HTTP en segundos",
    ["method", "endpoint", "status"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Métricas de errores HTTP
request_errors = Counter(
    "http_request_errors_total",
    "Total de errores HTTP",
    ["method", "endpoint", "error_type", "status_code"],
)

# Métricas de requests HTTP
request_total = Counter(
    "http_requests_total",
    "Total de requests HTTP",
    ["method", "endpoint", "status"],
)

# Métricas de disponibilidad por fuente meteorológica
source_availability = Gauge(
    "weather_source_availability",
    "Disponibilidad de fuentes meteorológicas (1=disponible, 0=no disponible)",
    ["source"],
)

# Métricas de circuit breaker
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Estado del circuit breaker (0=closed, 1=open, 2=half_open)",
    ["circuit_name"],
)

circuit_breaker_failures = Counter(
    "circuit_breaker_failures_total",
    "Total de fallos en circuit breaker",
    ["circuit_name"],
)

# Métricas de latencia por fuente
source_request_duration = Histogram(
    "weather_source_request_duration_seconds",
    "Duración de requests a fuentes meteorológicas",
    ["source", "operation"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Métricas de cache
cache_hits = Counter(
    "cache_hits_total",
    "Total de cache hits",
    ["cache_type"],
)

cache_misses = Counter(
    "cache_misses_total",
    "Total de cache misses",
    ["cache_type"],
)


def get_metrics() -> bytes:
    """
    Obtener métricas en formato Prometheus.

    Returns:
        Bytes con métricas en formato Prometheus
    """
    return generate_latest()


def record_request_metrics(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
) -> None:
    """
    Registrar métricas de un request HTTP.

    Args:
        method: Método HTTP (GET, POST, etc.)
        endpoint: Endpoint (ej: /api/v1/weather/current)
        status_code: Código de estado HTTP
        duration: Duración en segundos
    """
    # Normalizar endpoint (remover parámetros de query)
    normalized_endpoint = endpoint.split("?")[0] if "?" in endpoint else endpoint

    # Registrar duración
    request_duration.labels(
        method=method, endpoint=normalized_endpoint, status=status_code
    ).observe(duration)

    # Registrar total de requests
    request_total.labels(
        method=method, endpoint=normalized_endpoint, status=status_code
    ).inc()

    # Registrar errores si aplica
    if status_code >= 400:
        error_type = "client_error" if 400 <= status_code < 500 else "server_error"
        request_errors.labels(
            method=method,
            endpoint=normalized_endpoint,
            error_type=error_type,
            status_code=status_code,
        ).inc()


def record_source_availability(source: str, available: bool) -> None:
    """
    Registrar disponibilidad de una fuente meteorológica.

    Args:
        source: Nombre de la fuente (ej: "windy_ecmwf", "windy_gfs", "wrf_smn")
        available: True si está disponible, False si no
    """
    source_availability.labels(source=source).set(1 if available else 0)


def record_circuit_breaker_state(circuit_name: str, state: str) -> None:
    """
    Registrar estado de un circuit breaker.

    Args:
        circuit_name: Nombre del circuit breaker
        state: Estado ("closed", "open", "half_open")
    """
    state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
    circuit_breaker_state.labels(circuit_name=circuit_name).set(state_value)


def record_circuit_breaker_failure(circuit_name: str) -> None:
    """
    Registrar un fallo en un circuit breaker.

    Args:
        circuit_name: Nombre del circuit breaker
    """
    circuit_breaker_failures.labels(circuit_name=circuit_name).inc()


def record_source_request_duration(
    source: str, operation: str, duration: float
) -> None:
    """
    Registrar duración de un request a una fuente meteorológica.

    Args:
        source: Nombre de la fuente
        operation: Operación (ej: "get_current", "get_forecast")
        duration: Duración en segundos
    """
    source_request_duration.labels(source=source, operation=operation).observe(duration)


def record_cache_hit(cache_type: str) -> None:
    """
    Registrar un cache hit.

    Args:
        cache_type: Tipo de cache (ej: "weather_current", "weather_forecast")
    """
    cache_hits.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str) -> None:
    """
    Registrar un cache miss.

    Args:
        cache_type: Tipo de cache (ej: "weather_current", "weather_forecast")
    """
    cache_misses.labels(cache_type=cache_type).inc()
