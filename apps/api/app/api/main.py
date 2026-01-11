"""
Punto de entrada principal de la API FastAPI de SkyPulse.
Desplegado en Render.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import exception_handlers
from app.api.routers import weather, risk, alerts, patterns, health, metrics, auth
from app.api.middleware.correlation_id import CorrelationIDMiddleware
from app.api.middleware.metrics_middleware import MetricsMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.security_headers import SecurityHeadersMiddleware
from app.utils.exceptions import SkyPulseError
from app.utils.logging_config import setup_logging

# Cargar variables de entorno desde .env (desarrollo local)
# Buscar .env en la raíz del proyecto (2 niveles arriba desde apps/api/app/api/main.py)
env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[Config] Variables de entorno cargadas desde: {env_path}")
else:
    # También intentar desde la raíz del workspace
    root_env = Path(__file__).parent.parent.parent.parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
        print(f"[Config] Variables de entorno cargadas desde: {root_env}")
    else:
        print(
            "[Config] No se encontró archivo .env, usando variables de entorno del sistema"
        )

# Configurar logging estructurado JSON al inicio
setup_logging()

# Crear aplicación FastAPI
app = FastAPI(
    title="SkyPulse API",
    description="API de decisiones meteorológicas para Argentina",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS PRIMERO (antes de otros middlewares)
# CORS debe procesar las peticiones OPTIONS antes que otros middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
        "http://127.0.0.1:8080",
        "https://*.vercel.app",
        "https://skypulse.vercel.app",
        "https://skypulse-ar.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware de seguridad (orden importante: primero los más generales)
# CorrelationID debe ir después de CORS para que todos los logs lo incluyan
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(MetricsMiddleware)  # Métricas después de correlation ID
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Registrar exception handlers globales (orden importante: más específicos primero)
app.add_exception_handler(SkyPulseError, exception_handlers.skypulse_error_handler)
app.add_exception_handler(
    StarletteHTTPException, exception_handlers.http_exception_handler
)
app.add_exception_handler(
    RequestValidationError, exception_handlers.validation_exception_handler
)
app.add_exception_handler(Exception, exception_handlers.generic_exception_handler)

# Registrar routers con prefix /api/v1
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(weather.router, prefix="/api/v1", tags=["Weather"])
app.include_router(risk.router, prefix="/api/v1", tags=["Risk"])
app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])
app.include_router(patterns.router, prefix="/api/v1", tags=["Patterns"])


@app.get("/")
async def root() -> dict[str, str]:
    """Endpoint raíz con información de la API."""
    return {
        "name": "SkyPulse API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }
