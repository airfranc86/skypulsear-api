"""Middleware para registrar métricas de requests HTTP."""

import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.utils.metrics import record_request_metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware que registra métricas de cada request HTTP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Registrar métricas del request.
        
        Args:
            request: Request HTTP
            call_next: Función para continuar con el siguiente middleware
            
        Returns:
            Response HTTP
        """
        # Medir tiempo de inicio
        start_time = time.time()

        # Continuar con el request
        response = await call_next(request)

        # Calcular duración
        duration = time.time() - start_time

        # Registrar métricas
        record_request_metrics(
            method=request.method,
            endpoint=str(request.url.path),
            status_code=response.status_code,
            duration=duration,
        )

        return response


