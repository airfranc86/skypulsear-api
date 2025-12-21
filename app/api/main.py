"""
Punto de entrada principal de la API FastAPI de SkyPulse.
Desplegado en Render.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import weather, risk, alerts, patterns, health
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.api.middleware.security_headers import SecurityHeadersMiddleware

# Crear aplicación FastAPI
app = FastAPI(
    title="SkyPulse API",
    description="API de decisiones meteorológicas para Argentina",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware de seguridad (orden importante: primero los más generales)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Configurar CORS para permitir frontend en Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://*.vercel.app",
        "https://skypulse.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(health.router, tags=["Health"])
app.include_router(weather.router, prefix="/api/v1/weather", tags=["Weather"])
app.include_router(risk.router, prefix="/api/v1", tags=["Risk"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(patterns.router, prefix="/api/v1/patterns", tags=["Patterns"])


@app.get("/")
async def root() -> dict[str, str]:
    """Endpoint raíz con información de la API."""
    return {
        "name": "SkyPulse API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }
