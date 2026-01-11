"""
Authentication Router

User registration, login, and profile management endpoints.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.models.auth import (
    UserCreate,
    UserResponse,
    Token,
    UserProfileCreate,
    UserProfileResponse,
    APIKeyRequest,
    APIKeyResponse,
)
from app.services.auth_service import AuthService
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"username": username, "token": token}


class RegisterRequest(BaseModel):
    """Request para registro de usuario."""
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    """Request para login de usuario."""
    username: str
    password: str


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new user."""
    try:
        user_data = UserCreate(
            username=request.username,
            email=request.email,
            password=request.password
        )
        # Crear perfil por defecto
        from app.models.auth import UserType
        profile_data = UserProfileCreate(
            user_type=UserType.GENERAL,
            location=None,
            preferences=None
        )
        auth_service = AuthService()
        result = await auth_service.create_user(user_data, profile_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/login", response_model=dict)
async def login(request: LoginRequest):
    """Authenticate user."""
    try:
        auth_service = AuthService()
        result = await auth_service.authenticate_user(request.username, request.password)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    try:
        auth_service = AuthService()
        result = await auth_service.get_user_profile(current_user["username"])
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return result
    except Exception as e:
        logger.error(f"Profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_api_key(
    request: APIKeyRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Genera una API key para un servicio externo (ej: windy).
    
    Requiere autenticación Bearer token.
    """
    try:
        from app.utils.security import get_api_key as get_service_api_key
        
        # Obtener API key del servicio solicitado desde variables de entorno
        service_key = get_service_api_key(request.service)
        
        if not service_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key no configurada para el servicio: {request.service}",
            )
        
        # Retornar la API key (en producción, esto podría ser una key generada específica para el usuario)
        return APIKeyResponse(
            api_key=service_key,
            service=request.service,
            expires_at=None,  # Las keys del sistema no expiran
            rate_limit=1000,  # Límite por defecto
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando API key",
        )
