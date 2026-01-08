"""Exception handlers globales para FastAPI."""

import logging
from typing import Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.exceptions import (
    APIError,
    CircuitBreakerOpenError,
    DataValidationError,
    MeteosourceAPIError,
    RepositoryError,
    SkyPulseError,
    WeatherAPIError,
    WeatherDataError,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


async def skypulse_error_handler(
    request: Request, exc: Union[SkyPulseError, Exception]
) -> JSONResponse:
    """
    Handler para excepciones personalizadas de SkyPulse.

    Args:
        request: Request HTTP
        exc: Excepción de SkyPulse

    Returns:
        JSONResponse con formato de error consistente
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    # Determinar status code según tipo de excepción
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, DataValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, (MeteosourceAPIError, WeatherAPIError)):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, CircuitBreakerOpenError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, RepositoryError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    logger.error(
        "Error de SkyPulse capturado",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "status_code": status_code,
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": type(exc).__name__,
                "message": "Error al procesar la solicitud. Intente más tarde.",
                "correlation_id": correlation_id,
                "timestamp": None,  # Se agregará en el middleware si es necesario
            }
        },
    )


async def http_exception_handler(
    request: Request, exc: Union[StarletteHTTPException, Exception]
) -> JSONResponse:
    """
    Handler para HTTPException de Starlette/FastAPI.

    Args:
        request: Request HTTP
        exc: HTTPException

    Returns:
        JSONResponse con formato de error consistente
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    # Type-check to ensure we have HTTPException
    if not isinstance(exc, StarletteHTTPException):
        # Fallback for non-HTTPException types
        logger.error(
            "Non-HTTPException in http_exception_handler",
            extra={
                "error_type": type(exc).__name__,
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Error interno del servidor",
                    "correlation_id": correlation_id,
                }
            },
        )

    logger.warning(
        "HTTPException capturada",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else "Error HTTP",
                "correlation_id": correlation_id,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, Exception]
) -> JSONResponse:
    """
    Handler para errores de validación de Pydantic.

    Args:
        request: Request HTTP
        exc: RequestValidationError de Pydantic

    Returns:
        JSONResponse con formato de error consistente
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    # Type-check to ensure we have RequestValidationError
    if not isinstance(exc, RequestValidationError):
        # Fallback for non-RequestValidationError types
        logger.error(
            "Non-RequestValidationError in validation_exception_handler",
            extra={
                "error_type": type(exc).__name__,
                "correlation_id": correlation_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Error de validación en los datos de entrada",
                    "correlation_id": correlation_id,
                }
            },
        )

    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg"),
                "type": error.get("type"),
            }
        )

    logger.warning(
        "Error de validación de request",
        extra={
            "errors": errors,
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Error de validación en los datos de entrada",
                "correlation_id": correlation_id,
                "details": errors,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler genérico para excepciones no manejadas.

    Args:
        request: Request HTTP
        exc: Excepción no manejada

    Returns:
        JSONResponse con formato de error consistente
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.error(
        "Excepción no manejada capturada",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Error interno del servidor. Intente más tarde.",
                "correlation_id": correlation_id,
            }
        },
    )
