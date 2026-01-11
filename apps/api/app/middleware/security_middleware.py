"""
Security Middleware

Rate limiting, security headers, and request validation middleware.
"""

import time
import logging
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, Dict[str, Any]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to incoming requests."""
        # Skip health check and metrics endpoints
        if request.url.path in ["/health", "/metrics", "/"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries
        self.clients = {
            ip: (count, last_reset)
            for ip, (count, last_reset) in self.clients.items()
            if current_time - last_reset < self.period
        }

        # Check rate limit
        if client_ip in self.clients:
            count, last_reset = self.clients[client_ip]
            if current_time - last_reset < self.period:
                if count >= self.calls:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                self.clients[client_ip] = (count + 1, last_reset)
        else:
            self.clients[client_ip] = (1, current_time)

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to all responses."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
