"""Middleware para agregar correlation ID a cada request."""

import contextvars
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Context variable para almacenar correlation ID en el contexto de la request
correlation_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware que agrega correlation ID a cada request para trazabilidad."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Agregar correlation ID al request y response.

        Args:
            request: Request HTTP
            call_next: Función para continuar con el siguiente middleware

        Returns:
            Response HTTP con correlation ID en headers
        """
        # Obtener correlation ID del header o generar uno nuevo
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # Agregar al state de la request para acceso en endpoints
        request.state.correlation_id = correlation_id

        # Agregar al context variable para acceso en logging
        correlation_id_context.set(correlation_id)

        # Continuar con el request
        response = await call_next(request)

        # Agregar correlation ID al response header
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def get_correlation_id() -> str:
    """
    Obtener correlation ID del contexto actual.

    Returns:
        Correlation ID de la request actual o string vacío si no está disponible
    """
    return correlation_id_context.get("")
