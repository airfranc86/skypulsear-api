"""
Router de health check para Render.
"""

import os

from fastapi import APIRouter

from app.data.repositories.repository_factory import RepositoryFactory
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint para Render."""
    return {"status": "healthy", "service": "skypulse-api"}


@router.get("/debug/repos")
async def debug_repositories() -> dict:
    """
    Endpoint de debug para verificar repositorios y configuración.
    Solo para desarrollo/diagnóstico.
    """
    try:
        factory = RepositoryFactory()
        repos = factory.get_all_repositories()

        # Verificar variables de entorno (sin mostrar valores completos)
        env_status = {
            "METEOSOURCE_API_KEY": (
                "✅ Configurado"
                if os.getenv("METEOSOURCE_API_KEY")
                else "❌ No configurado"
            ),
            "WINDY_POINT_FORECAST_API_KEY": (
                "✅ Configurado" if os.getenv("WINDY_POINT_FORECAST_API_KEY") else "❌ No configurado"
            ),
            "VALID_API_KEYS": (
                "✅ Configurado" if os.getenv("VALID_API_KEYS") else "❌ No configurado"
            ),
        }

        # Intentar obtener datos de prueba de cada repositorio
        repos_status = {}
        for name, repo in repos.items():
            try:
                # Intentar obtener datos de Córdoba
                test_data = repo.get_current_weather(-31.42, -64.19)
                if test_data:
                    repos_status[name] = "✅ Funcionando"
                else:
                    repos_status[name] = "⚠️ Sin datos"
            except Exception as e:
                logger.warning(
                    "Error al verificar repositorio",
                    extra={
                        "repository": name,
                        "error_type": type(e).__name__,
                        "error_message": str(e)[:100],
                    },
                )
                repos_status[name] = f"❌ Error: {str(e)[:100]}"

        return {
            "repositories_available": list(repos.keys()),
            "repositories_status": repos_status,
            "environment_variables": env_status,
        }
    except Exception as e:
        logger.error(
            "Error en debug de repositorios",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        return {
            "error": "Error al inicializar repositorios",
            "message": "Ver logs para más detalles",
        }
