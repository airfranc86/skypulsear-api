"""
Router de health check para Render.
"""

import os
from typing import Dict, Any

from fastapi import APIRouter, Request

from app.data.repositories.repository_factory import RepositoryFactory
from app.utils.logging_config import get_logger
from app.api.dependencies import get_api_key_from_request

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint para Render."""
    return {"status": "healthy", "service": "skypulse-api"}


@router.get("/debug/api-key")
async def debug_api_key(request: Request) -> Dict[str, Any]:
    """
    Endpoint de diagnóstico para verificar recepción de API key.
    NO requiere autenticación - solo muestra qué está recibiendo el servidor.
    """
    # Obtener API key del request (si existe)
    api_key_received = get_api_key_from_request(request)
    
    # Obtener todos los headers
    all_headers = dict(request.headers)
    
    # Verificar configuración de VALID_API_KEYS
    valid_api_keys_env = os.getenv("VALID_API_KEYS", "")
    valid_api_keys_list = [key.strip() for key in valid_api_keys_env.split(",") if key.strip()]
    
    # Verificar si la API key recibida es válida
    is_valid = False
    if api_key_received and valid_api_keys_list:
        is_valid = api_key_received.strip() in valid_api_keys_list
    
    # Información del código (para verificar si es código nuevo)
    code_version = "NUEVO"  # Este mensaje solo existe en código nuevo
    
    return {
        "code_version": code_version,
        "api_key_received": api_key_received[:10] + "..." if api_key_received else None,
        "api_key_length": len(api_key_received) if api_key_received else 0,
        "api_key_valid": is_valid,
        "valid_api_keys_configured": len(valid_api_keys_list) > 0,
        "valid_api_keys_count": len(valid_api_keys_list),
        "headers_received": {
            k: v[:20] + "..." if len(v) > 20 else v 
            for k, v in all_headers.items()
        },
        "x_api_key_header": all_headers.get("X-API-Key") or all_headers.get("x-api-key") or "NO ENCONTRADO",
        "message": "Este endpoint muestra qué está recibiendo el servidor sin requerir autenticación"
    }


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
            "WINDY_POINT_FORECAST_API_KEY": (
                "✅ Configurado"
                if os.getenv("WINDY_POINT_FORECAST_API_KEY")
                else "❌ No configurado"
            ),
            "VALID_API_KEYS": (
                "✅ Configurado" if os.getenv("VALID_API_KEYS") else "❌ No configurado"
            ),
            "AWS_S3_BUCKET_NAME": (
                "✅ Configurado"
                if os.getenv("AWS_S3_BUCKET_NAME")
                else "⚠️ Usando default (smn-ar-wrf)"
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
