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
        key.strip() 
        for key in valid_api_keys_str.split(",") 
        if key.strip()
    ]
    return valid_api_keys


def get_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Optional[str]:
    """
    Valida API key del header.

    Retorna la API key si es válida, None si no se proporciona.
    """
    if not api_key:
        return None

    # API keys válidas (se recalculan en cada llamada)
    valid_api_keys = _get_valid_api_keys()

    if api_key in valid_api_keys:
        return api_key

    raise HTTPException(
        status_code=401,
        detail="API key inválida",
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
