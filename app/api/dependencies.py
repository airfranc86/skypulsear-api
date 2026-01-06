"""
Dependencias de seguridad para FastAPI.
"""

import os
from typing import Optional
from fastapi import Header, HTTPException, Security
from fastapi.security import APIKeyHeader

# API Key Header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Optional[str]:
    """
    Valida API key del header.

    Retorna la API key si es válida, None si no se proporciona.
    """
    if not api_key:
        return None

    # API keys válidas (en producción, esto vendría de Supabase)
    valid_api_keys = os.getenv("VALID_API_KEYS", "").split(",")
    valid_api_keys = [key.strip() for key in valid_api_keys if key.strip()]

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
