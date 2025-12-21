"""
Rate limiting middleware para FastAPI.
"""

import time
from collections import defaultdict
from typing import Callable
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Almacenamiento en memoria (en producción usar Redis)
_rate_limit_store: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting por IP.

    Límites:
    - Público: 60 requests/minuto
    - Con API Key: 1000 requests/hora
    """

    def __init__(
        self,
        app,
        public_limit: int = 60,
        public_window: int = 60,  # segundos
        api_key_limit: int = 1000,
        api_key_window: int = 3600,  # segundos
    ):
        super().__init__(app)
        self.public_limit = public_limit
        self.public_window = public_window
        self.api_key_limit = api_key_limit
        self.api_key_window = api_key_window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Obtener identificador (IP o API Key)
        client_ip = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key")

        identifier = api_key if api_key else f"ip:{client_ip}"

        # Determinar límites
        if api_key:
            limit = self.api_key_limit
            window = self.api_key_window
        else:
            limit = self.public_limit
            window = self.public_window

        # Limpiar requests antiguos
        now = time.time()
        key = f"{identifier}:{window}"

        if key in _rate_limit_store:
            _rate_limit_store[key] = [
                timestamp
                for timestamp in _rate_limit_store[key]
                if now - timestamp < window
            ]
        else:
            _rate_limit_store[key] = []

        # Verificar límite
        if len(_rate_limit_store[key]) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit excedido. Límite: {limit} requests por {window}s",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(window),
                },
            )

        # Registrar request
        _rate_limit_store[key].append(now)

        # Continuar con la request
        response = await call_next(request)

        # Agregar headers de rate limit
        remaining = limit - len(_rate_limit_store[key])
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + window))

        return response
