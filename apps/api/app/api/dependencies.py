"""
Dependencias de seguridad para FastAPI.
"""

import os
from typing import Optional
from fastapi import Header, HTTPException, Security
from fastapi.security import APIKeyHeader

# API Key Header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _get_valid_api_keys() -> list[str]:
    """
    Obtiene la lista de API keys válidas desde variables de entorno.
    Se recalcula en cada llamada para permitir cambios sin reiniciar.
    """
    valid_api_keys_str = os.getenv("VALID_API_KEYS", "")
    if not valid_api_keys_str:
        return []
    # Split por coma, limpiar espacios y filtrar vacíos
    valid_api_keys = [
        key.strip() for key in valid_api_keys_str.split(",") if key.strip()
    ]
    
    # Log para diagnóstico (solo en producción para verificar configuración)
    import logging
    logger = logging.getLogger(__name__)
    if valid_api_keys:
        # Log solo el número de keys y primeras letras por seguridad
        logger.debug(
            f"📋 API keys válidas cargadas: {len(valid_api_keys)} keys "
            f"(primera: {valid_api_keys[0][:10]}...)"
        )
    
    return valid_api_keys


def get_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Optional[str]:
    """
    Valida API key del header.

    Retorna la API key si es válida, None si no se proporciona.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not api_key:
        logger.debug("⚠️ No se recibió API key en header X-API-Key")
        return None

    # API keys válidas (se recalculan en cada llamada)
    valid_api_keys = _get_valid_api_keys()
    
    if not valid_api_keys:
        logger.error("❌ VALID_API_KEYS está vacío o no configurado en variables de entorno")
        raise HTTPException(
            status_code=500,
            detail="API key validation no configurada. Contacte al administrador.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Limpiar API key recibida (eliminar espacios al inicio/final)
    api_key_clean = api_key.strip()
    
    # Log de diagnóstico (solo primeros 10 caracteres por seguridad)
    logger.info(
        f"🔑 Validando API key recibida: '{api_key_clean[:10]}...' "
        f"(longitud: {len(api_key_clean)}, total válidas: {len(valid_api_keys)})"
    )

    # Verificar si la API key está en la lista (comparación exacta después de limpiar)
    if api_key_clean in valid_api_keys:
        logger.info(f"✅ API key válida: {api_key_clean[:10]}...")
        return api_key_clean

    # API key no válida - log detallado para diagnóstico
    logger.warning(
        f"❌ API key inválida: '{api_key_clean[:10]}...' "
        f"(longitud: {len(api_key_clean)}) "
        f"no está en lista de {len(valid_api_keys)} keys válidas. "
        f"Primera key válida: '{valid_api_keys[0][:10]}...' (longitud: {len(valid_api_keys[0])})"
    )
    
    raise HTTPException(
        status_code=401,
        detail="API key inválida. Proporcione una API key válida en el header X-API-Key.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def require_api_key(api_key: Optional[str] = Security(get_api_key)) -> str:
    """
    Requiere API key para endpoints protegidos.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key requerida. Proporcione X-API-Key en el header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


def optional_api_key(api_key: Optional[str] = Security(get_api_key)) -> Optional[str]:
    """
    API key opcional (para endpoints públicos con features premium).
    """
    return api_key
