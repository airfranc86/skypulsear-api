"""
Router de health check para Render.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint para Render."""
    return {"status": "healthy", "service": "skypulse-api"}
