"""Excepciones personalizadas para SkyPulse."""


class SkyPulseError(Exception):
    """Excepción base para errores de SkyPulse."""

    pass


class WeatherDataError(SkyPulseError):
    """Error relacionado con datos meteorológicos."""

    pass


class APIError(SkyPulseError):
    """Error en comunicación con APIs externas."""

    pass


class MeteosourceAPIError(APIError):
    """Error específico de la API de Meteosource."""

    pass


class WeatherAPIError(APIError):
    """Error genérico en APIs meteorológicas."""

    pass


class AWSConnectionError(APIError):
    """Error de conexión con AWS."""

    pass


class DataValidationError(WeatherDataError):
    """Error de validación de datos."""

    pass


class RepositoryError(SkyPulseError):
    """Error en repositorios de datos."""

    pass


class VerificationError(SkyPulseError):
    """Error en procesos de verificación."""

    pass


class CircuitBreakerOpenError(APIError):
    """Excepción lanzada cuando el circuit breaker está abierto."""

    pass